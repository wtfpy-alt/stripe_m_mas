from playwright.sync_api import sync_playwright
import time
import random
import re


def wait_for_and_click(page, selector, label, timeout=15000):
    try:
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click(timeout=timeout)
        print(f"✅ Clicked {label}")
        return True
    except Exception as exc:
        print(f"⚠️ Could not click {label}: {exc}")
        return False


def fill_card_field(page, selector, value, label, timeout=10000):
    try:
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        locator.fill(value)
        print(f"✅ Filled {label}")
        return True
    except Exception as exc:
        print(f"⚠️ Could not fill {label}: {exc}")
        return False


def get_checkout_frame(page, timeout=20000):
    try:
        page.wait_for_selector('iframe.razorpay-checkout-frame', timeout=timeout)
    except Exception as exc:
        print(f"⚠️ No checkout iframe found: {exc}")
        return None

    return page.frame_locator('iframe.razorpay-checkout-frame')


def automate_vriksha_payment():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=700)
        page = browser.new_page()

        print("🚀 Opening Payment Page...")
        page.goto("https://pages.razorpay.com/pl_Qhw5srUaiC30d5/view", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # === PREVIOUS WORKING FIELD FILLING ===
        try:
            page.fill('input[type="number"], input[placeholder*="amount" i]', "700")
            page.fill('input[placeholder*="email" i], input[name*="email" i]', "testuser@gmail.com")
            page.fill('input[aria-label="Enter your Phone"], input[type="tel"]', "916463344567")

            invoice = str(random.randint(100000, 999999))
            page.fill('input[placeholder*="invoice" i], input[name*="invoice" i]', invoice)

            page.fill('input[name="service_availed"], input[aria-label*="Service" i]', "Gardening")
            print("✅ All custom fields filled")
        except Exception as exc:
            print(f"⚠️ Some custom fields missed: {exc}")

        page.wait_for_timeout(3000)

        # Click Main Pay Button
        if not wait_for_and_click(page, 'button:has-text("Pay"), button:has-text("Proceed")', "main Pay button", timeout=15000):
            print("⚠️ Click Pay button manually")

        page.wait_for_timeout(6000)

        checkout_frame = get_checkout_frame(page, timeout=20000)
        if checkout_frame is None:
            print("⚠️ Checkout iframe not found. Card automation may not work.")
            checkout_frame = page
        else:
            print("✅ Checkout iframe detected")

        # === NEW: SELECT CARDS & FILL CARD DETAILS ===
        print("Trying to select Cards...")
        cards_selected = (
            wait_for_and_click(checkout_frame, 'span[data-testid="Cards"]', "Cards option", timeout=20000)
            or wait_for_and_click(checkout_frame, 'span:has-text("Cards")', "Cards option", timeout=20000)
            or wait_for_and_click(checkout_frame, 'text=Cards', "Cards option", timeout=20000)
        )
        if not cards_selected:
            print("⚠️ Could not auto-select Cards → Click 'Cards' manually")

        # Re-acquire the iframe in case the checkout widget reloaded
        if checkout_frame is not page:
            checkout_frame = get_checkout_frame(page, timeout=20000)

        page.wait_for_timeout(3000)

        # Fill Card Details before continuing
        print("💳 Filling Test Card first...")
        card_ok = fill_card_field(checkout_frame, 'input[name="card.number"]', "4111111111111111", "card number")
        expiry_ok = fill_card_field(checkout_frame, 'input[name="card.expiry"]', "12/28", "card expiry")
        cvv_ok = fill_card_field(checkout_frame, 'input[name="card.cvv"]', "123", "card CVV")
        name_ok = fill_card_field(checkout_frame, 'input[name="card.name"]', "Test User", "card name")

        if card_ok and expiry_ok and cvv_ok and name_ok:
            print("✅ Test Card filled")
        else:
            print("⚠️ Could not fill card details automatically")

        page.wait_for_timeout(2000)

        # Click Continue after filling fields
        if not wait_for_and_click(checkout_frame, 'button:has-text("Continue")', "Continue button", timeout=20000):
            print("⚠️ Click Continue manually")
        else:
            print("✅ Continue clicked")
            maybe_later_clicked = wait_for_and_click(
                checkout_frame,
                'button[name="pay_without_saving_card"]',
                "Maybe later button",
                timeout=20000,
            ) or wait_for_and_click(
                checkout_frame,
                'button:has-text("Maybe later")',
                "Maybe later button",
                timeout=20000,
            )

            if maybe_later_clicked:
                print("✅ Clicked Maybe later")
            else:
                print("⚠️ Could not click Maybe later button")

            try:
                description = checkout_frame.locator('[data-testid="retry-description"]').first
                description.wait_for(state="visible", timeout=15000)
                text = description.inner_text().strip()
                print(f"📣 Retry response: {text}")
            except Exception as exc:
                print(f"⚠️ Could not read retry response: {exc}")

            try:
                if checkout_frame.locator('text=International cards are not supported').count() > 0:
                    print("⚠️ Detected unsupported card error: International cards are not supported.")
                    print("   Use a locally issued Indian card or a Razorpay-supported test card instead of 4111 1111 1111 1111.")
            except Exception:
                pass

        print("\n" + "="*80)
        print("Script finished. Now complete OTP / final step manually.")
        print("="*80)

        input("\nPress Enter after payment is complete...")

        browser.close()


if __name__ == "__main__":
    automate_vriksha_payment()
