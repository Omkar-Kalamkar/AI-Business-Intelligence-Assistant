import { afterEach, describe, expect, it, vi } from "vitest";

import { api, downloadReport, getApiError, TOKEN_KEY } from "./api";

describe("api helpers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns server validation messages when available", () => {
    const error = { response: { data: { detail: "Bad dataset." } } };

    expect(getApiError(error, "Fallback")).toBe("Bad dataset.");
    expect(getApiError({}, "Fallback")).toBe("Fallback");
  });

  it("downloads a PDF using the server filename", async () => {
    const createObjectURL = vi.fn(() => "blob:report");
    const revokeObjectURL = vi.fn();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    Object.defineProperty(URL, "createObjectURL", {
      value: createObjectURL,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjectURL,
      configurable: true,
    });

    vi.spyOn(api, "get").mockResolvedValue({
      data: new Blob(["%PDF-1.7"], { type: "application/pdf" }),
      headers: {
        "content-disposition": 'attachment; filename="sales_7.pdf"',
      },
    });

    const filename = await downloadReport(7);

    expect(api.get).toHaveBeenCalledWith("/report/7", {
      responseType: "blob",
    });
    expect(filename).toBe("sales_7.pdf");
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:report");
  });

  it("falls back to a safe filename when the header is missing", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    Object.defineProperty(URL, "createObjectURL", {
      value: vi.fn(() => "blob:report"),
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: vi.fn(),
      configurable: true,
    });

    vi.spyOn(api, "get").mockResolvedValue({
      data: new Blob(["%PDF-1.7"]),
      headers: {},
    });

    expect(await downloadReport()).toBe("business-insights.pdf");
  });

  it("sends the stored access token as a bearer header", async () => {
    const originalAdapter = api.defaults.adapter;
    const adapter = vi.fn(async (config) => ({
      data: {},
      status: 200,
      statusText: "OK",
      headers: {},
      config
    }));

    api.defaults.adapter = adapter;
    window.localStorage.setItem(TOKEN_KEY, "test-token");

    try {
      await api.get("/auth/me");
      expect(adapter.mock.calls[0][0].headers.Authorization).toBe(
        "Bearer test-token"
      );
    } finally {
      window.localStorage.removeItem(TOKEN_KEY);
      api.defaults.adapter = originalAdapter;
    }
  });
});
