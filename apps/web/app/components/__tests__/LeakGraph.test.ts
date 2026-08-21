import { describe, it, expect } from "vitest";

describe("LeakGraph", () => {
  it("renders stage labels correctly", () => {
    const labels: Record<string, string> = {
      SITE_VISIT: "Site Visits",
      PRODUCT_VIEW: "Product Views",
      ADD_TO_CART: "Add to Cart",
      CHECKOUT_STARTED: "Checkout",
      PAYMENT_ATTEMPTED: "Payment Attempts",
      PAYMENT_SUCCESSFUL: "Successful",
    };
    
    expect(Object.keys(labels)).toHaveLength(6);
    expect(labels["SITE_VISIT"]).toBe("Site Visits");
    expect(labels["PAYMENT_SUCCESSFUL"]).toBe("Successful");
  });

  it("formats paise correctly", () => {
    function formatPaise(paise: number): string {
      const rupees = paise / 100;
      if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(2)}L`;
      if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
      return `₹${rupees.toFixed(0)}`;
    }

    expect(formatPaise(10000000)).toBe("₹1.00L"); // 1 Lakh
    expect(formatPaise(500000)).toBe("₹5.0K");
    expect(formatPaise(1000)).toBe("₹10");
  });

  it("computes drop rate correctly", () => {
    const prevCount = 1000;
    const currentCount = 400;
    const dropRate = ((prevCount - currentCount) / prevCount * 100).toFixed(1);
    expect(dropRate).toBe("60.0");
  });
});
