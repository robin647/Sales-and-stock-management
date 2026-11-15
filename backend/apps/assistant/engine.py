"""Read-only business answers assembled from approved ORM lookups."""
import re
from hashlib import sha256
from datetime import date
from decimal import Decimal
from django.core import signing
from django.db.models import Q, Sum
from django.utils import timezone
from .language import has, intent, match_entities, period, normalize

SALT = "mahir-local-assistant-v1"
HELP = "আমি কর্মীর বেতন/অনুপস্থিতি, মূল স্টক, পার্টির পেমেন্ট/বকেয়া, সেলাইয়ের লট/অপারেটর, প্রডিউসার এবং শোরুমের হিসাব দেখতে পারি। উদাহরণ: ‘রবিনের এই মাসে অনুপস্থিতি কত?’ বা ‘৩৩ নম্বর লট কে সেলাই করেছে?’ নাম বা কোডসহ প্রশ্ন করুন।"
LABELS = {"employee": "কর্মী", "party": "পার্টি", "stock": "প্রোডাক্ট", "swing": "সেলাই অপারেটর", "producer": "প্রডিউসার", "showroom": "শোরুম"}
FOLLOWUP_WORDS = set(normalize("koto koi koy din ar abar salary beton betan absent attendance leave due baki payment last net loan advance bonus overtime paid ase ache chilo kobe kokhon tarikh date total how much when was it কত কয় দিন আর আবার বেতন অনুপস্থিত ছুটি বাকি বকেয়া পেমেন্ট শেষ নিট ঋণ অগ্রিম বোনাস ওভারটাইম আছে ছিল কবে কখন তারিখ মোট").split())


def money(value):
    return f"৳{Decimal(value or 0):,.2f}"


def context_token(user, data):
    return signing.dumps({"user": user.pk, **data}, salt=SALT, compress=True)


def read_context(user, token):
    if not token:
        return {}
    try:
        data = signing.loads(token, salt=SALT, max_age=1800)
        return data if data.get("user") == user.pk else {}
    except signing.BadSignature:
        return {}


def catalog(domain):
    from apps.employees.models import Employee
    from apps.wholesale.models import WholesaleParty
    from apps.products.models import Product
    from apps.swing.models import SwingOperator
    from apps.producers.models import Producer
    from apps.showrooms.models import Showroom
    models = {"employee": Employee, "party": WholesaleParty, "stock": Product, "swing": SwingOperator, "producer": Producer, "showroom": Showroom}
    model = models[domain]
    qs = model.objects.all()
    if domain == "stock":
        qs = qs.filter(sales_channel="main")
    rows = []
    fields = ["id", "name", "is_active"]
    if domain == "employee": fields.append("employee_id")
    if domain == "stock": fields.append("code")
    for obj in qs.values(*fields):
        code = obj.get("employee_id", "") or obj.get("code", "") or ""
        name = obj["name"]
        rows.append({"id": obj["id"], "name": name, "code": code,
                     "label": f"{name} · {code}" if code else name,
                     "is_active": obj["is_active"]})
    return rows


def format_reply(answer, user, ctx, *, sources=None, choices=None):
    return {"answer": answer, "context": context_token(user, ctx), "sources": sources or [],
            "choices": choices or [], "mode": "local", "as_of": timezone.now().isoformat()}


def choose(domain, question, previous, *, force=False):
    rows = catalog(domain)
    matches = match_entities(question, rows)
    if matches:
        if matches[0]["score"] >= .93 and (len(matches) == 1 or matches[0]["score"] - matches[1]["score"] > .035):
            return matches[0], []
        return None, matches[:5]
    if previous.get("domain") == domain and previous.get("entity"):
        # Context contains only signed, server-selected identities. Never accept an arbitrary model or query.
        pronoun = has(question, "or", "tar", "onar", "unir", "ওর", "তার", "উনার", "তিনি", "তারপর", "same", "ager", "আগের")
        words = normalize(question).split()
        generic = bool(words) and all(word in FOLLOWUP_WORDS for word in words)
        if force or pronoun or generic:
            return next((row for row in rows if row["id"] == previous["entity"]), None), []
    return None, []


def respond(user, question, token=""):
    previous = read_context(user, token)
    if has(question, "password", "পাসওয়ার্ড", "পাসওয়ার্ড", "api key", "secret key", "access token", "nid", "এনআইডি"):
        return format_reply("পাসওয়ার্ড, টোকেন, API key বা ব্যক্তিগত পরিচয়পত্রের তথ্য দেখাই না। ব্যবসার হিসাব সম্পর্কে প্রশ্ন করুন।", user, {})
    if has(question, "delete", "মুছে", "ডিলিট", "update", "আপডেট", "পরিবর্তন কর", "edit", "বদলে", "truncate", "drop table", "insert into"):
        return format_reply("আমি শুধু তথ্য পড়ে উত্তর দিই। কোনো রেকর্ড যোগ, পরিবর্তন বা মুছি না। পরিবর্তনের জন্য সংশ্লিষ্ট অ্যাডমিন ফর্ম ব্যবহার করুন।", user, previous)
    dates = period(question)
    if dates and dates.get("error"):
        return format_reply(dates["error"], user, previous)
    domain = intent(question, previous.get("domain"))
    # Follow-up payment/due questions retain an explicitly selected producer/operator.
    if domain == "party" and previous.get("domain") in ("producer", "swing", "employee") and has(question, "or", "tar", "ওর", "তার", "উনার"):
        domain = previous["domain"]
    selected = None
    alternatives = []
    if domain in LABELS:
        if previous.get("selection") == sha256(question.encode()).hexdigest() and previous.get("domain") == domain:
            selected = next((row for row in catalog(domain) if row["id"] == previous.get("entity")), None)
        else:
            selected, alternatives = choose(domain, question, previous)
    elif domain == "unknown" and has(question, "earn", "earns", "koto", "pay", "monthly", "কত", "পায়", "পায়", "মাসে", "মাসিক", "পদ", "designation"):
        candidates = []
        for item in ("employee", "party", "swing", "producer", "stock", "showroom"):
            matches = match_entities(question, catalog(item))
            candidates.extend((row["score"], item, row) for row in matches if row["score"] >= .93)
        candidates.sort(key=lambda item: -item[0])
        if candidates and (len(candidates) == 1 or candidates[0][0] - candidates[1][0] > .035):
            _, domain, selected = candidates[0]
    ctx = {"domain": domain}
    if dates:
        ctx["period"] = dates
    elif previous.get("domain") == domain and previous.get("period"):
        ctx["period"] = previous["period"]
    dates = ctx.get("period")
    if alternatives:
        # A selection re-runs the original question, preserving its requested metric and period.
        choices = [{"label": f"{row['label']}{' (নিষ্ক্রিয়)' if not row['is_active'] else ''}",
                    "question": question, "context": context_token(user, {**ctx, "entity": row["id"], "selection": sha256(question.encode()).hexdigest()})}
                   for row in alternatives]
        return format_reply(f"কোন {LABELS[domain]} বোঝাচ্ছেন? একাধিক কাছাকাছি নাম মিলেছে। নিচে সঠিকটি বেছে নিন।", user, ctx, choices=choices)
    if selected:
        ctx["entity"] = selected["id"]
    if domain == "lot":
        return lot_answer(user, question, ctx, previous)
    if domain == "business":
        return business_answer(user, ctx)
    if domain == "stock" and not selected and not alternatives and has(question, "total", "mot", "মোট", "all", "সব", "main", "মূল", "পুরো"):
        return stock_answer(user, None, ctx)
    if domain == "swing" and not selected and has(question, "total", "mot", "মোট", "summary", "সারাংশ"):
        return swing_answer(user, None, ctx)
    if domain == "party" and not selected and not alternatives and has(question, "total", "mot", "মোট", "all", "সব", "overall", "summary", "সারাংশ"):
        return wholesale_totals_answer(user, ctx)
    if domain == "employee" and not selected and not alternatives and has(question, "total", "mot", "মোট", "all", "সব", "highest", "beshi", "বেশি", "সর্বোচ্চ"):
        return employee_totals_answer(user, ctx, question)
    if domain in LABELS and not selected:
        return format_reply(f"কোন {LABELS[domain]} বোঝাচ্ছেন তা নিশ্চিত হতে পারিনি। সঠিক নাম বা কোড লিখুন; যেমন ‘রবিনের বেতন কত’ অথবা ‘Bor Kone পার্টির শেষ পেমেন্ট কত’।", user, ctx)
    handlers = {"employee": employee_answer, "party": party_answer, "stock": stock_answer,
                "swing": swing_answer, "producer": producer_answer, "showroom": showroom_answer}
    if domain in handlers:
        return handlers[domain](user, selected, ctx, question=question)
    return format_reply(HELP, user, {})


def employee_answer(user, selected, ctx, question=""):
    from apps.employees.models import Employee, SalaryEntry
    employee = Employee.objects.get(pk=selected["id"])
    payroll = has(question, "attendance", "হাজিরা", "absent", "absence", "অনুপস্থিত", "leave", "ছুটি", "chuti", "net", "হাতে", "pabe", "পাবে", "কর্তন", "deduction", "overtime", "ওভারটাইম", "loan", "advance", "অগ্রিম", "bonus", "বোনাস")
    lines = [f"{employee.name} ({employee.employee_id})", f"• পদ: {employee.designation}", f"• বর্তমান মূল মাসিক বেতন: {money(employee.salary)}"]
    if not employee.is_active:
        lines.append("• কর্মীটি বর্তমানে নিষ্ক্রিয়।")
    sources = [f"Employee #{employee.pk}"]
    if payroll or ctx.get("period"):
        chosen = ctx.get("period")
        today = timezone.localdate()
        month = date.fromisoformat(chosen["start"]).replace(day=1) if chosen else today.replace(day=1)
        if not chosen:
            lines.append(f"সময়সীমা উল্লেখ না থাকায় চলতি মাস ({month:%Y-%m}) দেখছি।")
        entry = SalaryEntry.objects.filter(employee=employee, month=month).first()
        if not entry:
            lines.append(f"{month:%Y-%m} মাসের বেতন শিট পাওয়া যায়নি। তাই অনুপস্থিতি, কর্তন বা নিট বেতন নিশ্চিত করে বলা যাচ্ছে না।")
        else:
            lines.extend([f"{entry.month:%Y-%m} বেতন শিট:", f"• অনুপস্থিত: {entry.absent_days} দিন; ছুটি: {entry.leave_days} দিন",
                          f"• ওই মাসের মূল বেতন: {money(entry.base_salary)}", f"• অনুপস্থিতির কর্তন: {money(entry.absence_amount)}",
                          f"• ছুটির সমন্বয়: {money(entry.leave_amount)}", f"• ওভারটাইম: {entry.overtime_hours} ঘণ্টা — {money(entry.overtime_pay)}",
                          f"• হাজিরা বোনাস: {money(entry.attendance_bonus)}", f"• অগ্রিম কর্তন: {money(entry.advance_deduction)}; ঋণ কর্তন: {money(entry.loan)}",
                          f"• অন্যান্য কর্তন: {money(entry.other_deduction)}", f"• নিট প্রাপ্য বেতন: {money(entry.net_salary)}",
                          "নিট প্রাপ্য মানে হিসাব করা বেতন; এটি বেতন পরিশোধের প্রমাণ নয়।"])
            if has(question, "kon din", "কোন দিন", "কোন কোন", "which days"):
                lines.append("এই শিটে মাসের মোট অনুপস্থিতির দিন আছে; ঠিক কোন কোন তারিখে অনুপস্থিত ছিলেন তা রেকর্ড করা নেই।")
            sources.append(f"SalaryEntry #{entry.pk} · {entry.month:%Y-%m}")
            lines.append(f"• ওই মাসের অগ্রিম ব্যালান্স: {money(entry.advance_balance)}; বকেয়া ঋণ: {money(entry.outstanding_loan)}")
        ctx["period"] = {"start": month.isoformat(), "end": month.isoformat(), "label": month.strftime("%Y-%m")}
    return format_reply("\n".join(lines), user, ctx, sources=sources)


def employee_totals_answer(user, ctx, question):
    from apps.employees.models import Employee
    employees = Employee.objects.filter(is_active=True)
    if ctx.get("period"):
        return format_reply("নির্দিষ্ট মাসের বেতন/অনুপস্থিতি জানতে কর্মীর নাম দিন। কর্মীদের মোট মূল বেতন জানতে সময়সীমা ছাড়া প্রশ্ন করুন।", user, {"domain": "employee"})
    totals = employees.aggregate(total=Sum("salary"))
    lines = [f"সক্রিয় কর্মী: {employees.count()} জন", f"• সবার বর্তমান মূল মাসিক বেতন: {money(totals['total'])}", "এটি মূল বেতন; কর্তনসহ নিট বেতন বা পরিশোধের মোট নয়।"]
    if has(question, "highest", "beshi", "বেশি", "সর্বোচ্চ"):
        lines.append("মূল বেতন অনুযায়ী শীর্ষ সর্বোচ্চ ৫ জন:")
        lines.extend(f"• {row['name']} ({row['employee_id']}) — {money(row['salary'])}" for row in employees.order_by("-salary", "pk").values("name", "employee_id", "salary")[:5])
    return format_reply("\n".join(lines), user, ctx, sources=["Employee · active employees, basic salaries"])


def wholesale_totals_answer(user, ctx):
    from apps.wholesale.services import all_party_summary
    params = {}
    dates = ctx.get("period")
    if dates:
        params.update(start_date=dates["start"], end_date=dates["end"])
    rows, totals = all_party_summary(params)
    lines = [f"পাইকারি সারাংশ ({dates['label'] if dates else 'সব সময়'}):", f"• নিট বিক্রি: {money(totals['total_sales'])}",
             f"• পেমেন্ট: {money(totals['total_payments'])}", f"• লেজারের বকেয়া: {money(totals['total_due'])}",
             f"• অগ্রিম/ক্রেডিট: {money(totals['total_credit'])}", f"• বকেয়া − ক্রেডিট: {money(totals['total_due'] - totals['total_credit'])}"]
    if dates: lines.append("এটি নির্দিষ্ট সময়ের রিপোর্ট; আগের সব লেনদেনের বর্তমান বকেয়া নয়।")
    return format_reply("\n".join(lines), user, ctx, sources=["Wholesale invoice + Easy wholesale summary"])


def payment_rows(party_id, dates=None):
    from apps.wholesale.models import WholesalePayment, EasyWholesalePayment
    result = []
    for model, filters, source in ((WholesalePayment, {"invoice__party_id": party_id}, "Invoice payment"), (EasyWholesalePayment, {"party_id": party_id}, "Easy wholesale payment")):
        rows = model.objects.filter(**filters)
        if dates:
            rows = rows.filter(payment_date__range=[dates["start"], dates["end"]])
        for row in rows.order_by("-payment_date", "-created_at", "-pk")[:10]:
            result.append({"date": row.payment_date, "created": row.created_at, "id": row.pk, "amount": row.total_amount,
                           "bank": row.bank_amount, "bkash": row.bkash_amount, "cash": row.cash_amount,
                           "reference": row.reference, "source": source})
    return sorted(result, key=lambda row: (row["date"], row["created"], row["id"]), reverse=True)


def party_answer(user, selected, ctx, question=""):
    from apps.wholesale.services import all_party_summary
    rows, _ = all_party_summary({"party": selected["id"]})
    row = rows[0]
    lines = [f"{row['party_name']} — পাইকারি হিসাব", f"• মোট নিট বিক্রি: {money(row['total_sales'])}",
             f"• মোট জমা/পেমেন্ট: {money(row['total_payments'])}", f"• লেজারের মোট বকেয়া: {money(row['total_due'])}",
             f"• অগ্রিম/ক্রেডিট: {money(row['total_credit'])}"]
    lines.extend([f"• বকেয়া − ক্রেডিট, নিট অবস্থান: {money(row['total_due'] - row['total_credit'])}", "লেজারের বকেয়া ও ক্রেডিট আলাদা দেখানো হয়েছে; কোনো সমন্বয় বা রেকর্ড পরিবর্তন করা হয়নি।"])
    dates = ctx.get("period")
    payments = payment_rows(selected["id"], dates)
    sources = [f"WholesaleParty #{selected['id']} · Invoice + Easy wholesale ledger"]
    if dates:
        lines.append(f"নিচের পেমেন্ট অনুসন্ধান {dates['label']} সময়ের; উপরের বকেয়া সব সময়ের মোট হিসাব।")
    if payments:
        payment = payments[0]
        lines.extend([f"• শেষ পেমেন্ট: {money(payment['amount'])} — {payment['date'].isoformat()}",
                      f"  ব্যাংক {money(payment['bank'])}, বিকাশ {money(payment['bkash'])}, নগদ {money(payment['cash'])}"])
        if payment["reference"]:
            lines.append(f"  রেফারেন্স: {payment['reference']}")
        sources.append(f"{payment['source']} #{payment['id']}")
        if has(question, "history", "ইতিহাস", "list", "তালিকা", "sob payment", "সব পেমেন্ট"):
            lines.append("সর্বশেষ সর্বোচ্চ ১০টি পেমেন্ট:")
            lines.extend(f"• {p['date'].isoformat()} — {money(p['amount'])} ({p['source']})" for p in payments[:10])
    else:
        lines.append("এই সময়সীমায় কোনো পেমেন্টের রেকর্ড নেই।" if dates else "এখনো কোনো পেমেন্টের রেকর্ড নেই।")
    return format_reply("\n".join(lines), user, ctx, sources=sources)


def stock_answer(user, selected, ctx, question=""):
    from apps.products.models import Product
    from apps.inventory.models import FactoryStock, ShowroomStock
    if ctx.get("period"):
        return format_reply("স্টক টেবিলে বর্তমান পরিমাণ থাকে। ওই তারিখের মূল/কারখানা স্টক নিশ্চিতভাবে বলতে পারছি না। বর্তমান স্টক জানতে তারিখ ছাড়া আবার প্রশ্ন করুন।", user, {"domain": "stock", **({"entity": selected["id"]} if selected else {})})
    if not selected:
        factory = FactoryStock.objects.filter(product__sales_channel="main").aggregate(total=Sum("quantity"))["total"] or 0
        showroom = ShowroomStock.objects.filter(product__sales_channel="main").aggregate(total=Sum("quantity"))["total"] or 0
        return format_reply(f"বর্তমান মূল স্টক:\n• কারখানা: {factory} পিস\n• সব শোরুম: {showroom} পিস\n• মোট: {factory + showroom} পিস\nঅনলাইনের আলাদা স্টক এই হিসাবে অন্তর্ভুক্ত নয়।", user, ctx, sources=["FactoryStock + ShowroomStock · main channel"])
    product = Product.objects.get(pk=selected["id"], sales_channel="main")
    factory = FactoryStock.objects.filter(product=product).values_list("quantity", flat=True).first() or 0
    stores = list(ShowroomStock.objects.filter(product=product).select_related("showroom"))
    lines = [f"{product.name} · {product.code}{' · ' + product.size if product.size else ''}", f"• কারখানা: {factory} পিস"]
    lines.extend(f"• {row.showroom.name}: {row.quantity} পিস" for row in stores)
    lines.extend([f"• মোট মূল স্টক: {factory + sum(row.quantity for row in stores)} পিস", f"• মূল ক্যাটালগের বিক্রয় মূল্য: {money(product.selling_price)}", "অনলাইন স্টক/দাম এই হিসাবের অংশ নয়।"])
    return format_reply("\n".join(lines), user, ctx, sources=[f"Product #{product.pk} · main inventory"])


def lot_answer(user, question, ctx, previous):
    from apps.swing.models import SwingLot
    text = question.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    match = re.search(r"(?:lot|লট)\s*(?:number|no\.?|নম্বর|নং|#)?\s*[:#-]?\s*([a-z]*[-/]?\d+[a-z0-9/-]*)", text, re.I)
    if not match:
        match = re.search(r"(\d+[a-z0-9/-]*)\s*(?:number|no\.?|নম্বর|নং)?\s*(?:lot|লট)", text, re.I)
    number = match.group(1) if match else previous.get("lot_number")
    if not number:
        return format_reply("লট নম্বরটি লিখুন। যেমন ‘৩৩ নম্বর লট কে সেলাই করেছে?’", user, {"domain": "lot"})
    bengali_number = number.translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))
    qs = SwingLot.objects.select_related("operator").filter(Q(lot_number__icontains=number) | Q(lot_number__icontains=bengali_number))
    if ctx.get("period"):
        qs = qs.filter(lot_date__range=[ctx["period"]["start"], ctx["period"]["end"]])
    lots = []
    for lot in qs.order_by("-lot_date", "-pk"):
        stored = re.sub(r"^(?:lot|lt)(?: number| no)?\s*", "", normalize(lot.lot_number))
        if stored == normalize(number) or stored.isdigit() and number.isdigit() and int(stored) == int(number):
            lots.append(lot)
    ctx["lot_number"] = number
    if not lots:
        return format_reply(f"{number} নম্বর লটের রেকর্ড পাওয়া যায়নি। সংরক্ষিত লট নম্বর বা কোডটি যাচাই করুন।", user, ctx)
    lines = [f"{number} নম্বর লট — {len(lots)}টি রেকর্ড মিলেছে।"]
    for lot in lots[:10]:
        lines.extend([f"• {lot.lot_number}: সেলাই অপারেটর {lot.operator.name}",
                      f"  তারিখ {lot.lot_date.isoformat()} · {lot.quantity} পিস · রেট {money(lot.rate)}",
                      f"  কাটিং মাস্টার: {lot.cutting_master_name or 'রেকর্ড করা নেই'}"])
        if not lot.is_active: lines.append("  রেকর্ডটি বর্তমানে নিষ্ক্রিয়।")
    if len(lots) > 10: lines.append("প্রথম ১০টি দেখানো হয়েছে; আরও নির্দিষ্ট লট কোড দিন।")
    return format_reply("\n".join(lines), user, ctx, sources=[f"SwingLot #{lot.pk}" for lot in lots[:10]])


def swing_answer(user, selected, ctx, question=""):
    from apps.swing.views import _dashboard_data
    data = _dashboard_data()
    rows = [row for row in data["operators"] if not selected or row["id"] == selected["id"]]
    if ctx.get("period"):
        return format_reply("সেলাইয়ের এই সারাংশ সব সময়ের হিসাব। নির্দিষ্ট সময়ের সেলাই জানতে লট নম্বরসহ প্রশ্ন করুন।", user, {"domain": "swing", **({"entity": selected["id"]} if selected else {})})
    if not rows:
        return format_reply("সক্রিয় সেলাই অপারেটরের হিসাব পাওয়া যায়নি।", user, ctx)
    lines = ["সেলাইয়ের হিসাব (সব সময়):"]
    for row in rows[:10]:
        lines.extend([f"{row['name']}", f"• কাজ: {row['total_products']} পিস; বাতিল: {row['rejected_products']} পিস",
                      f"• মোট কাজের মূল্য: {money(row['total_work_amount'])}", f"• পরিশোধ: {money(row['total_paid'])}; বাকি: {money(row['total_due'])}"])
    if len(rows) > 10: lines.append("প্রথম ১০ জন দেখানো হয়েছে; নির্দিষ্ট অপারেটরের নাম লিখুন।")
    return format_reply("\n".join(lines), user, ctx, sources=["Swing operator dashboard · active records"])


def producer_answer(user, selected, ctx, question=""):
    from apps.producers.models import Producer, ProducerCost, ProducerPayment
    producer = Producer.objects.get(pk=selected["id"])
    costs = ProducerCost.objects.filter(producer=producer, is_active=True)
    payments = ProducerPayment.objects.filter(producer=producer, is_active=True)
    if ctx.get("period"):
        p = ctx["period"]
        costs = costs.filter(transaction_date__range=[p["start"], p["end"]])
        payments = payments.filter(payment_date__range=[p["start"], p["end"]])
    cost = costs.aggregate(total=Sum("total_cost"))["total"] or 0
    paid = payments.aggregate(total=Sum("amount"))["total"] or 0
    lines = [f"{producer.name} — প্রডিউসারের হিসাব ({ctx.get('period', {}).get('label', 'সব সময়')})",
             f"• খরচ: {money(cost)}", f"• পরিশোধ: {money(paid)}", f"• পার্থক্য: {money(cost - paid)}"]
    last = payments.order_by("-payment_date", "-created_at", "-pk").first()
    if last: lines.append(f"• শেষ পেমেন্ট: {money(last.amount)} — {last.payment_date.isoformat()}")
    else: lines.append("এই সময়ে পেমেন্টের রেকর্ড নেই।")
    if ctx.get("period"): lines.append("এটি নির্বাচিত সময়ের লেনদেন; আগের জের অন্তর্ভুক্ত নয়।")
    return format_reply("\n".join(lines), user, ctx, sources=[f"Producer #{producer.pk} · active costs/payments"])


def showroom_answer(user, selected, ctx, question=""):
    from apps.inventory.models import DailyBalance, DailyStock
    dates = ctx.get("period")
    if not dates:
        return format_reply("কোন তারিখ বা মাসের শোরুমের হিসাব দেখতে চান? যেমন ‘আজ’ অথবা ‘2026-11’।", user, ctx)
    rows = DailyBalance.objects.filter(showroom_id=selected["id"], date__range=[dates["start"], dates["end"]])
    if not rows.exists():
        return format_reply(f"{selected['name']} শোরুমের {dates['label']} সময়ের হিসাব পাওয়া যায়নি।", user, ctx)
    totals = rows.aggregate(**{field: Sum(field) for field in ("total_sale", "cash_sale", "card_sale", "expense", "salary", "deposit")})
    last = rows.order_by("-date", "-pk").first()
    sold = DailyStock.objects.filter(showroom_id=selected["id"], date__range=[dates["start"], dates["end"]]).aggregate(total=Sum("sold_qty"))["total"] or 0
    lines = [f"{selected['name']} · {dates['label']}", f"• বিক্রি: {money(totals['total_sale'])}; পণ্য {sold} পিস",
             f"• নগদ: {money(totals['cash_sale'])}; কার্ড: {money(totals['card_sale'])}", f"• খরচ: {money(totals['expense'])}; বেতন খরচ: {money(totals['salary'])}",
             f"• জমা: {money(totals['deposit'])}", f"• সর্বশেষ নথিভুক্ত সমাপনী ব্যালান্স ({last.date.isoformat()}): {money(last.closing_balance)}"]
    return format_reply("\n".join(lines), user, ctx, sources=[f"DailyBalance + DailyStock · showroom #{selected['id']}"])


def business_answer(user, ctx):
    from apps.wholesale.services import all_party_summary
    from apps.inventory.models import FactoryStock, ShowroomStock
    if ctx.get("period"):
        return format_reply("নির্দিষ্ট সময়ের জন্য পার্টি বা শোরুমের নামসহ প্রশ্ন করুন। সর্বকালের মূল স্টক/পাইকারি সারাংশ পেতে ‘ব্যবসার সারাংশ’ লিখুন।", user, {"domain": "business"})
    _, totals = all_party_summary({})
    factory = FactoryStock.objects.filter(product__sales_channel="main").aggregate(total=Sum("quantity"))["total"] or 0
    stores = ShowroomStock.objects.filter(product__sales_channel="main").aggregate(total=Sum("quantity"))["total"] or 0
    lines = ["মূল ব্যবসার সারাংশ (সব সময়):", f"• মূল/কারখানা স্টক: {factory} পিস; শোরুমগুলোতে: {stores} পিস",
             f"• পাইকারি নিট বিক্রি: {money(totals['total_sales'])}", f"• পাইকারি পেমেন্ট: {money(totals['total_payments'])}",
             f"• পাইকারি বকেয়া: {money(totals['total_due'])}", "এটি মূল স্টক ও পাইকারি সারাংশ; অনলাইন বিক্রি বা লাভের হিসাব নয়।"]
    return format_reply("\n".join(lines), user, ctx, sources=["Main inventory + wholesale summary"])
