import re
from datetime import date

from pyscript import document, window, when
from pyscript.ffi import create_proxy

# ---------------------------------------------------------------- data
# Replace with the real Facebook Messenger link (e.g. https://m.me/yourpage).
MESSENGER_URL = "REPLACE_WITH_TABLEA_TO_GO_MESSENGER_LINK"

# Proposed prices from the feasibility study. Single source of truth.
PRODUCTS = [
    {"id": "tablea", "name": "Tablea Tablet Pack", "price": 150, "drink": False, "art": "art-tablet",
     "desc": "10 tablea tablets in a resealable pack. Ideal for making traditional Filipino cacao drinks."},
    {"id": "sikwate", "name": "Ready-to-Drink Sikwate", "price": 80, "drink": True, "art": "art-cup",
     "desc": "12 oz cup. Available hot or cold."},
    {"id": "gift", "name": "Tablea To-Go Gift Box", "price": 350, "drink": False, "art": "art-box",
     "desc": "Tablea tablets and sikwate mix in a gift box with a card."},
    {"id": "sachet", "name": "Sikwate Mix Sachet", "price": 40, "drink": False, "art": "art-sachet",
     "desc": "Single-serving sachet. Convenient for preparing a cacao drink."},
]
BY_ID = {p["id"]: p for p in PRODUCTS}
MAX_QTY = 99
cart = {}  # product id -> quantity


# ------------------------------------------------------------- helpers
def qs(selector):
    return document.querySelector(selector)


def peso(amount):
    return f"₱{amount:,}"


def cart_total():
    return sum(BY_ID[pid]["price"] * qty for pid, qty in cart.items())


def cart_count():
    return sum(cart.values())


def toast(message):
    """Short feedback message after every user action."""
    box = qs("#toast")
    box.textContent = message
    box.classList.add("show")
    window.setTimeout(create_proxy(lambda: box.classList.remove("show")), 2400)


def go_to(selector):
    """Scroll to a section and flash it so the person sees where they landed."""
    target = qs(selector)
    if target:
        target.scrollIntoView()
        target.classList.remove("flash")
        _ = target.offsetWidth  # force reflow so the animation can replay
        target.classList.add("flash")


# ----------------------------------------------------------- rendering
def render_products():
    html = ""
    for p in PRODUCTS:
        html += f"""
        <article class="card product" id="product-{p['id']}">
          <div class="art {p['art']}" role="img" aria-label="Sample image of {p['name']}"><span>Sample image</span></div>
          <h3>{p['name']}</h3>
          <p class="price">{peso(p['price'])}</p>
          <p>{p['desc']}</p>
          <div class="buy">
            <label for="qty-{p['id']}">Quantity</label>
            <input class="qty-input" id="qty-{p['id']}" data-id="{p['id']}" type="number" min="1" max="{MAX_QTY}" value="1">
            <span class="sub" id="sub-{p['id']}">{peso(p['price'])}</span>
          </div>
          <button class="btn add-btn" data-id="{p['id']}">Add to cart</button>
        </article>"""
    html += """
        <article class="card product" id="product-bulk">
          <div class="art art-bulk" role="img" aria-label="Sample image of custom orders"><span>Sample image</span></div>
          <h3>Custom and Bulk Orders</h3>
          <p class="price">Price by quotation</p>
          <p>For events, giveaways, and pasalubong orders.</p>
          <button class="btn btn-alt bulk-btn">Request a quotation</button>
        </article>"""
    qs("#product-grid").innerHTML = html


def render_cart():
    box = qs("#cart-items")
    if not cart:
        box.innerHTML = '<p class="empty">Your cart is empty. Add a product above to get started.</p>'
    else:
        html = ""
        for pid, qty in cart.items():
            p = BY_ID[pid]
            html += f"""
            <li class="cart-line">
              <div><strong>{p['name']}</strong><small>{peso(p['price'])} each</small></div>
              <div class="stepper">
                <button data-act="dec" data-id="{pid}" aria-label="Decrease {p['name']}">−</button>
                <span aria-live="polite">{qty}</span>
                <button data-act="inc" data-id="{pid}" aria-label="Increase {p['name']}">+</button>
              </div>
              <strong>{peso(p['price'] * qty)}</strong>
              <button class="link-btn" data-act="remove" data-id="{pid}">Remove</button>
            </li>"""
        box.innerHTML = html
    qs("#cart-total").textContent = peso(cart_total())
    qs("#cart-count").textContent = str(cart_count())
    qs("#clear-cart").disabled = not cart
    qs("#checkout").disabled = not cart


def render_order_selection():
    """Read-only list of cart items inside the order form (same data as the cart)."""
    box = qs("#order-selection")
    if not cart:
        box.innerHTML = '<p class="empty">No products selected yet. Add items from the Products section, or tick the custom/bulk box below.</p>'
    else:
        rows = "".join(
            f"<li><span>{qty} × {BY_ID[pid]['name']}</span><span>{peso(BY_ID[pid]['price'] * qty)}</span></li>"
            for pid, qty in cart.items()
        )
        box.innerHTML = f'<ul class="summary-list">{rows}</ul><p class="total-row">Total <strong>{peso(cart_total())}</strong></p>'
    # Drink temperature only applies when sikwate is in the cart.
    qs("#temp-field").hidden = "sikwate" not in cart


def refresh():
    """Re-draw every part of the page that depends on the cart."""
    render_cart()
    render_order_selection()


# ------------------------------------------------- product grid events
@when("click", "#product-grid")
def on_product_click(event):
    """Button-click events: Add to cart and Request a quotation (event delegation)."""
    add = event.target.closest(".add-btn")
    if add:
        pid = add.dataset.id
        field = qs(f"#qty-{pid}")
        qty = max(1, min(MAX_QTY, int(field.value or 1)))
        cart[pid] = min(MAX_QTY, cart.get(pid, 0) + qty)
        field.value = 1
        update_card_subtotal(pid)
        refresh()
        toast(f"Added {qty} × {BY_ID[pid]['name']} to your cart.")
    elif event.target.closest(".bulk-btn"):
        qs("#is-bulk").checked = True
        go_to("#order")
        qs("#notes").focus()
        toast("Custom/bulk inquiry selected. Tell us what you need in the notes.")


def update_card_subtotal(pid):
    qty = max(1, min(MAX_QTY, int(qs(f"#qty-{pid}").value or 1)))
    qs(f"#sub-{pid}").textContent = peso(BY_ID[pid]["price"] * qty)


@when("change", "#product-grid")
def on_quantity_change(event):
    """Quantity-change event: clamp the value and recalculate the card subtotal."""
    field = event.target
    if not field.classList.contains("qty-input"):
        return
    try:
        value = int(field.value)
    except ValueError:
        value = 1
    field.value = max(1, min(MAX_QTY, value))
    update_card_subtotal(field.dataset.id)


# ------------------------------------------------------- cart events
@when("click", "#cart-items")
def on_cart_click(event):
    """Increase, decrease and remove buttons inside the cart."""
    btn = event.target.closest("button[data-act]")
    if not btn:
        return
    pid, act = btn.dataset.id, btn.dataset.act
    if act == "inc":
        cart[pid] = min(MAX_QTY, cart[pid] + 1)
    elif act == "dec":
        cart[pid] -= 1
        if cart[pid] <= 0:
            del cart[pid]
    elif act == "remove":
        del cart[pid]
        toast(f"Removed {BY_ID[pid]['name']}.")
    refresh()


@when("click", "#clear-cart")
def on_clear_cart(event):
    cart.clear()
    refresh()
    toast("Cart cleared.")


@when("click", "#checkout")
def on_checkout(event):
    go_to("#order")


# ------------------------------------------- promos / navigation events
@when("click", ".promo-btn")
def on_promo_click(event):
    """Promotion and hero buttons scroll to the product or section named in data-target."""
    go_to(event.currentTarget.dataset.target)


@when("click", "#nav-toggle")
def on_nav_toggle(event):
    nav = qs("#nav-links")
    nav.classList.toggle("open")
    qs("#nav-toggle").setAttribute("aria-expanded", "true" if nav.classList.contains("open") else "false")


@when("click", "#nav-links a")
def on_nav_link(event):
    qs("#nav-links").classList.remove("open")


# ------------------------------------------------- order form events
def set_error(field_id, message):
    """Show or clear an error message under a form field."""
    field, err = qs(f"#{field_id}"), qs(f"#err-{field_id}")
    err.textContent = message
    if message:
        field.setAttribute("aria-invalid", "true")
    else:
        field.removeAttribute("aria-invalid")
    return message


def validate_order():
    """Returns a list of (field_id, message) for every problem found."""
    problems = []
    name = qs("#cust-name").value.strip()
    contact = qs("#contact").value.strip()
    if len(name) < 2:
        problems.append(("cust-name", "Enter your name (at least 2 characters)."))
    if len(contact) < 5:
        problems.append(("contact", "Enter a mobile number, email, or Messenger name so we can reach you."))
    elif "@" in contact and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", contact):
        problems.append(("contact", "That email address doesn't look right. Check it and try again."))
    if not qs("#fulfillment").value:
        problems.append(("fulfillment", "Choose pickup, meet-up, or delivery."))
    if "sikwate" in cart and not qs("#temperature").value:
        problems.append(("temperature", "Choose hot or cold for your sikwate."))
    if not cart and not qs("#is-bulk").checked:
        problems.append(("order-selection-error", "Add at least one product, or tick the custom/bulk inquiry box."))
    return problems


def build_summary():
    lines = ["TABLEA TO-GO - ORDER REQUEST (not confirmed until the seller replies)", ""]
    lines.append(f"Name: {qs('#cust-name').value.strip()}")
    lines.append(f"Contact: {qs('#contact').value.strip()}")
    lines.append("Items:")
    if cart:
        for pid, qty in cart.items():
            p = BY_ID[pid]
            lines.append(f"  - {qty} x {p['name']} @ {peso(p['price'])} = {peso(p['price'] * qty)}")
        lines.append(f"Total: {peso(cart_total())}")
    else:
        lines.append("  (none selected)")
    if qs("#is-bulk").checked:
        lines.append("Custom/bulk inquiry: yes (price by quotation)")
    if "sikwate" in cart:
        lines.append(f"Sikwate temperature: {qs('#temperature').value}")
    lines.append(f"Pickup/meet-up/delivery: {qs('#fulfillment').value}")
    when_text = qs("#when").value.strip()
    if when_text:
        lines.append(f"Preferred date/time: {when_text}")
    notes = qs("#notes").value.strip()
    if notes:
        lines.append(f"Notes: {notes}")
    return "\n".join(lines)


@when("submit", "#order-form")
def on_order_submit(event):
    """Form-submission event: validate, then prepare (not send) an order summary."""
    event.preventDefault()
    for fid in ("cust-name", "contact", "fulfillment", "temperature"):
        set_error(fid, "")
    qs("#err-order-selection-error").textContent = ""
    problems = validate_order()
    if problems:
        for fid, message in problems:
            if fid == "order-selection-error":
                qs("#err-order-selection-error").textContent = message
            else:
                set_error(fid, message)
        first = problems[0][0]
        if first != "order-selection-error":
            qs(f"#{first}").focus()
        qs("#order-result").hidden = True
        toast("Please fix the highlighted fields.")
        return
    qs("#summary-text").textContent = build_summary()
    qs("#order-result").hidden = False
    qs("#order-result").scrollIntoView()
    toast("Order request prepared. It has not been sent yet.")


@when("input", "#order-form")
def on_order_input(event):
    """Clear a field's error message as soon as the person edits it."""
    fid = event.target.id
    if fid and qs(f"#err-{fid}"):
        set_error(fid, "")


@when("click", "#copy-summary")
def on_copy_summary(event):
    text = qs("#summary-text").textContent
    try:
        window.navigator.clipboard.writeText(text)
        toast("Order summary copied.")
    except Exception:
        toast("Couldn't copy automatically. Select the text and copy it manually.")


@when("click", ".messenger-btn")
def on_messenger(event):
    """Opens Messenger only once a real link is configured in MESSENGER_URL."""
    if MESSENGER_URL.startswith("REPLACE"):
        toast("Messenger link isn't set yet. Add the real link to MESSENGER_URL in main.py.")
    else:
        window.open(MESSENGER_URL, "_blank")


@when("click", "#new-order")
def on_new_order(event):
    cart.clear()
    qs("#order-form").reset()
    qs("#order-result").hidden = True
    refresh()
    toast("Started a new order.")


# ----------------------------------------------------- contact form
@when("submit", "#contact-form")
def on_contact_submit(event):
    event.preventDefault()
    name = qs("#c-name").value.strip()
    message = qs("#c-message").value.strip()
    out = qs("#contact-result")
    if len(name) < 2 or len(message) < 5:
        out.className = "notice error"
        out.textContent = "Enter your name and a message (at least 5 characters)."
        return
    out.className = "notice"
    out.textContent = (f"Thanks, {name}. Your inquiry is ready, but this demo site has no backend, "
                       "so nothing was sent. Please message the Tablea To-Go page on Messenger.")
    qs("#contact-form").reset()


# ------------------------------------------------------------ startup
render_products()
refresh()
qs("#year").textContent = str(date.today().year)
qs("#loading").hidden = True


