from insight_utils import round_or_none

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
MAX_RECOMMENDATIONS = 8


def _evidence(label, value, fmt="number"):
    return {"label": label, "value": value, "format": fmt}


def generate_recommendations(analysis, anomalies=None, trends=None,
                             root_cause=None, alerts=None):
    recommendations = []
    summary = (analysis or {}).get("summary", {})

    if anomalies and anomalies.get("available"):
        severe = [
            item for item in anomalies["anomalies"]
            if item["severity"] in ("critical", "high")
        ]

        if severe:
            worst = severe[0]
            top_flag = (
                worst["flagged_columns"][0]
                if worst["flagged_columns"] else None
            )

            evidence = [
                _evidence("Unusual records", anomalies["anomaly_count"]),
                _evidence("High/critical records", len(severe)),
            ]
            reason = (
                f"{len(severe)} record(s) deviate strongly from typical "
                f"values (robust z-score >= 4.5 or Isolation Forest flag)."
            )

            if top_flag:
                evidence.append(
                    _evidence(
                        f"Row {worst['row_index']} {top_flag['column']}",
                        top_flag["value"],
                    )
                )
                evidence.append(
                    _evidence(
                        f"Typical {top_flag['column']} (median)",
                        top_flag["expected_median"],
                    )
                )
                reason += (
                    f" The strongest deviation is row "
                    f"{worst['row_index']} where {top_flag['column']} = "
                    f"{top_flag['value']} versus a typical value of "
                    f"{top_flag['expected_median']}."
                )

            recommendations.append({
                "id": "investigate_anomalies",
                "title": "Investigate unusual transactions",
                "recommendation": (
                    "Review the flagged records with your sales/finance "
                    "team to confirm whether they are genuine business "
                    "events or data entry errors before acting on them."
                ),
                "reason": reason,
                "priority": "high",
                "evidence": evidence,
            })

    if trends and trends.get("available") and trends.get("anomaly_count"):
        flagged = [
            period for period in trends["periods"]
            if period["is_anomaly"]
        ]
        worst_period = max(flagged, key=lambda p: abs(p["zscore"]))

        recommendations.append({
            "id": "review_unusual_periods",
            "title": "Review unusual sales periods",
            "recommendation": (
                f"Examine what happened in {worst_period['period']} "
                f"(promotions, stock-outs, pricing or one-off orders) "
                f"and check whether the pattern is repeating."
            ),
            "reason": (
                f"{trends['anomaly_count']} period(s) fall far outside "
                f"the typical sales range. {worst_period['period']} is "
                f"{worst_period['direction']} the median by "
                f"{abs(worst_period['deviation_pct'] or 0):.2f}%."
            ),
            "priority": "high",
            "evidence": [
                _evidence("Period", worst_period["period"], "text"),
                _evidence("Period sales", worst_period["sales"], "currency"),
                _evidence(
                    "Typical period sales (median)",
                    trends["expected_median_sales"],
                    "currency",
                ),
                _evidence(
                    "Deviation from median",
                    worst_period["deviation_pct"],
                    "percent",
                ),
            ],
        })

    if root_cause and root_cause.get("available") and (
        root_cause.get("mode") == "period_comparison"
    ):
        total_change = root_cause.get("total_change") or 0
        change_pct = root_cause.get("total_change_pct")
        top_mover = root_cause.get("top_mover")

        if total_change < 0 and (change_pct is None or change_pct <= -10):
            negative_contributors = []
            for breakdown in root_cause["dimensions"]:
                for contributor in breakdown["contributors"]:
                    if contributor["change"] < 0:
                        negative_contributors.append(
                            (breakdown["dimension"], contributor)
                        )
            negative_contributors.sort(
                key=lambda pair: pair[1]["change"]
            )

            evidence = [
                _evidence(
                    "Sales change",
                    root_cause["total_change"],
                    "currency",
                ),
                _evidence(
                    "Sales change %", change_pct, "percent"
                ),
            ]
            reason = (
                f"Sales fell from {root_cause['previous_total']:,.2f} "
                f"({root_cause['previous_period']}) to "
                f"{root_cause['current_total']:,.2f} "
                f"({root_cause['current_period']})."
            )

            if negative_contributors:
                dimension, contributor = negative_contributors[0]
                evidence.append(
                    _evidence(
                        f"{contributor['name']} ({dimension}) change",
                        contributor["change"],
                        "currency",
                    )
                )
                if contributor["contribution_pct"] is not None:
                    evidence.append(
                        _evidence(
                            f"{contributor['name']} share of decline",
                            contributor["contribution_pct"],
                            "percent",
                        )
                    )
                reason += (
                    f" {contributor['name']} ({dimension}) accounts for "
                    f"the largest recorded decrease "
                    f"({contributor['change']:+,.2f})."
                )

            recommendations.append({
                "id": "address_sales_decline",
                "title": "Address the sales decline",
                "recommendation": (
                    "Start with the largest declining items below: "
                    "check pricing, availability and recent customer "
                    "feedback for them before wider changes."
                ),
                "reason": reason,
                "priority": "high",
                "evidence": evidence,
            })

        elif total_change > 0 and change_pct is not None and change_pct >= 10:
            evidence = [
                _evidence(
                    "Sales change", root_cause["total_change"], "currency"
                ),
                _evidence("Sales change %", change_pct, "percent"),
            ]
            reason = (
                f"Sales grew from {root_cause['previous_total']:,.2f} "
                f"({root_cause['previous_period']}) to "
                f"{root_cause['current_total']:,.2f} "
                f"({root_cause['current_period']})."
            )

            if top_mover:
                evidence.append(
                    _evidence(
                        f"{top_mover['name']} ({top_mover['dimension']}) change",
                        top_mover["change"],
                        "currency",
                    )
                )
                reason += (
                    f" {top_mover['name']} ({top_mover['dimension']}) "
                    f"contributed the largest increase "
                    f"({top_mover['change']:+,.2f})."
                )

            recommendations.append({
                "id": "sustain_growth",
                "title": "Validate and sustain the growth",
                "recommendation": (
                    "Confirm the growth is repeatable (not a one-off "
                    "order) and ensure stock and staffing can support "
                    "the higher demand level."
                ),
                "reason": reason,
                "priority": "medium",
                "evidence": evidence,
            })

    total_sales = summary.get("total_sales") or 0
    total_profit = summary.get("total_profit") or 0

    if total_profit < 0:
        recommendations.append({
            "id": "fix_negative_profit",
            "title": "Restore profitability",
            "recommendation": (
                "Review cost structure, discounting and pricing on "
                "loss-making lines before pursuing volume growth."
            ),
            "reason": (
                f"Recorded profit is negative ({total_profit:,.2f}) "
                f"against sales of {total_sales:,.2f}."
            ),
            "priority": "high",
            "evidence": [
                _evidence("Total profit", total_profit, "currency"),
                _evidence("Total sales", total_sales, "currency"),
            ],
        })

    elif total_sales > 0:
        margin = total_profit / total_sales * 100

        if margin < 10:
            recommendations.append({
                "id": "improve_margin",
                "title": "Improve profit margin",
                "recommendation": (
                    "Audit high-cost products and supplier terms; "
                    "small margin gains compound across all sales."
                ),
                "reason": (
                    f"Overall profit margin is {margin:.2f}%, below a "
                    f"10% reference threshold."
                ),
                "priority": "medium",
                "evidence": [
                    _evidence(
                        "Profit margin", round_or_none(margin), "percent"
                    ),
                    _evidence("Total profit", total_profit, "currency"),
                    _evidence("Total sales", total_sales, "currency"),
                ],
            })

    product_data = (analysis or {}).get("product_data") or []
    if product_data and total_sales > 0 and len(product_data) > 1:
        top_product = max(product_data, key=lambda item: item["sales"])
        share = top_product["sales"] / total_sales * 100

        if share >= 40:
            recommendations.append({
                "id": "reduce_concentration",
                "title": "Reduce product concentration risk",
                "recommendation": (
                    f"Grow secondary products so the business is less "
                    f"dependent on {top_product['name']}."
                ),
                "reason": (
                    f"{top_product['name']} accounts for {share:.2f}% "
                    f"of total sales; a drop in this single product "
                    f"would materially affect revenue."
                ),
                "priority": "medium",
                "evidence": [
                    _evidence(
                        f"{top_product['name']} sales",
                        top_product["sales"],
                        "currency",
                    ),
                    _evidence(
                        "Share of total sales",
                        round_or_none(share),
                        "percent",
                    ),
                ],
            })

    missing_values = summary.get("missing_values") or 0
    if missing_values > 0:
        recommendations.append({
            "id": "improve_data_quality",
            "title": "Fix missing data",
            "recommendation": (
                "Fill or correct missing fields at the source so "
                "future analyses and alerts stay reliable."
            ),
            "reason": (
                f"The dataset contains {missing_values} missing "
                f"value(s), which can distort totals and detection."
            ),
            "priority": "low",
            "evidence": [
                _evidence("Missing values", missing_values),
            ],
        })

    if not recommendations:
        evidence = []
        if total_sales:
            evidence.append(
                _evidence("Total sales", total_sales, "currency")
            )
        if total_profit:
            evidence.append(
                _evidence("Total profit", total_profit, "currency")
            )

        recommendations.append({
            "id": "monitor",
            "title": "No critical issues detected",
            "recommendation": (
                "Keep monitoring KPIs and upload fresh data regularly "
                "so new anomalies and changes are caught early."
            ),
            "reason": (
                "No severe anomalies, significant KPI swings or "
                "profitability problems were found in this dataset."
            ),
            "priority": "low",
            "evidence": evidence,
        })

    recommendations.sort(key=lambda item: PRIORITY_RANK[item["priority"]])
    return recommendations[:MAX_RECOMMENDATIONS]
