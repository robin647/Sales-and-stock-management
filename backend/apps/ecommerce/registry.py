from . import models

# One schema drives API metadata and the typed admin forms.
MODULES = {
    "brands": (models.Brand, "Brands", "Build the identities behind your online collection."),
    "vendors": (models.Vendor, "Multi-vendor Management", "Approve vendors, track contacts and record commission agreements."),
    "suppliers": (models.Supplier, "Suppliers", "Your online purchasing partners and contact directory."),
    "purchases": (models.Purchase, "Suppliers & Purchases", "Draft a purchase, then mark it received to replenish online stock once."),
    "payments": (models.Payment, "Payments", "Record and verify manual payments, COD collections and refunds. No money is transferred here."),
    "returns": (models.ReturnRequest, "Returns & Refunds", "Request → approve → receive. Restock only inspected online items; record refunds separately."),
    "shipping": (models.ShippingZone, "Shipping & Delivery", "District delivery rates are applied at checkout. Courier bookings are managed with your courier."),
    "reviews": (models.Review, "Reviews & Ratings", "Moderate product feedback and publish approved reviews."),
    "support": (models.SupportTicket, "Customer Support", "Track enquiries, priorities and customer-visible replies."),
    "content": (models.ContentPage, "Website Content", "Publish pages, FAQs and store banners. Drafts stay private."),
    "campaigns": (models.Campaign, "Marketing & Promotions", "Schedule website announcements and plan campaigns. External messages are not sent automatically."),
    "finance": (models.LedgerEntry, "Finance & Accounting", "Record online income and expenses independently of showroom accounts."),
    "seo": (models.SeoEntry, "SEO Management", "Manage page titles, descriptions and canonical links for public store pages."),
    "locales": (models.Locale, "Language & Currency", "Enable storefront languages and display currencies. Checkout settlement remains in BDT."),
    "team": (models.TeamMember, "Employees & Roles", "Create dedicated ecommerce logins with module-specific permissions; main business access stays restricted."),
}

READ_ONLY = {"id", "created_at", "updated_at", "user"}
