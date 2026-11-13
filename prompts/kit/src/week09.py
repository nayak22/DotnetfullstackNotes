import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "SOLID part 1: Single Responsibility and Open/Closed",
"Recognise classes that do too much or must be edited for every new rule, and refactor them into small, focused types that are open for extension.",
[("SOLID","Five object-oriented design principles (SRP, OCP, LSP, ISP, DIP) collected by Robert C. Martin to keep code easy to change."),
("Single Responsibility Principle (SRP)","A class should have one reason to change, i.e. answer to one actor or business concern."),
("Reason to change","A source of change requests: tax rules (finance), storage (DBA), email provider (ops), log format (support)."),
("Cohesion","How closely the members of a class belong together. High cohesion = every member serves one purpose."),
("Coupling","How much one type depends on the details of another. Low coupling = changes don't ripple."),
("God class","A class that knows and does too much; the classic SRP violation (\"OrderManager\", \"Utils\", \"Helper\")."),
("Open/Closed Principle (OCP)","Software entities should be open for extension but closed for modification: add behaviour by adding code, not editing tested code."),
("Extension point","A seam (interface, abstract method, delegate, event) where new behaviour can be plugged in."),
("Polymorphism","Calling the same member on different types and getting type-specific behaviour (Week 2)."),
("Shotgun surgery","A smell where one change forces edits in many places; often caused by a switch repeated across files."),
("Refactoring","Changing the structure of code without changing its behaviour."),
("YAGNI","\"You aren't gonna need it\": don't build extension points for variations that don't exist yet."),
("Rule of three","Tolerate duplication or a switch twice; abstract when the third variation appears.")],
["SRP is about <i>reasons to change</i>, not \"one method per class\".",
"A good SRP split usually leaves a thin orchestrator that calls focused collaborators.",
"OCP doesn't mean you never edit a file; it means adding a new variant shouldn't require editing existing, tested variants.",
"The usual OCP tools in C#: interfaces + polymorphism, abstract classes, delegates, and registering implementations in a list or dictionary.",
"A <code>switch</code> on a closed set (e.g. an enum that will never grow) is fine; a switch on a growing business list is a smell.",
"SOLID is a set of heuristics, not laws. Over-applying them produces \"interface soup\"."],
f'''
<h3>1. The five principles at a glance</h3>
{table(["Letter","Principle","One-line meaning","Smell when violated"],[
["S","Single Responsibility","One reason to change","A class touched by every feature; 800-line services"],
["O","Open/Closed","Extend by adding code, not editing it","A switch you edit for every new type"],
["L","Liskov Substitution","Subtypes must work wherever the base type is expected","Overrides that throw NotSupportedException or <code>if (x is Square)</code> checks"],
["I","Interface Segregation","Clients shouldn't depend on methods they don't use","Implementations full of empty methods"],
["D","Dependency Inversion","Depend on abstractions; high-level policy doesn't know low-level details","<code>new SqlConnection()</code> inside business logic"]])}
<p>You have already used several of these: Week 2's <code>IClock</code> and interfaces were DIP, Week 2's Template Method was OCP, and Week 4's <code>IRepository&lt;T&gt;</code> split storage from library rules (SRP). Today and tomorrow give them names and sharpen the judgement of when to apply them.</p>

<h3>2. SRP — before: an InvoiceService that does everything</h3>
{C(r"""
public class InvoiceService
{
    public void CreateInvoice(string customerEmail, string buyerState,
                              List<(string Item, decimal Price, int Qty)> lines)
    {
        // 1. Calculate (finance team changes GST rules)
        decimal subtotal = 0;
        foreach (var l in lines) subtotal += l.Price * l.Qty;
        decimal tax = subtotal * 0.18m;                     // GST… but CGST+SGST or IGST?
        decimal total = subtotal + tax;

        // 2. Save (DBA wants SQL Server instead of CSV)
        File.AppendAllText("invoices.csv", $"{DateTime.Now:O},{customerEmail},{total}\n");

        // 3. Email (ops wants a different provider)
        Console.WriteLine($"[SMTP] To {customerEmail}: your invoice total is ₹{total:N2}");

        // 4. Log (support wants structured logs)
        Console.WriteLine($"[LOG] Invoice created for {customerEmail}");
    }
}
""", "Before/InvoiceService.cs")}
<p>Four different people can ask for changes to this one method. You can't unit test the GST calculation without writing a file and "sending" an email, and a bug fix in the CSV format risks breaking tax.</p>

<h3>3. SRP — after: focused collaborators plus a thin orchestrator</h3>
{C(r"""
namespace Billing;

public record InvoiceLine(string Item, decimal UnitPrice, int Quantity)
{
    public decimal Amount => UnitPrice * Quantity;
}

public record Invoice(string Number, string CustomerEmail, IReadOnlyList<InvoiceLine> Lines,
                      decimal Subtotal, decimal Cgst, decimal Sgst, decimal Igst)
{
    public decimal Total => Subtotal + Cgst + Sgst + Igst;
}

// Responsibility 1: tax rules (pure, easy to unit test)
public class GstCalculator
{
    public (decimal Cgst, decimal Sgst, decimal Igst) Calculate(decimal subtotal, string sellerState, string buyerState)
    {
        if (string.Equals(sellerState, buyerState, StringComparison.OrdinalIgnoreCase))
        {
            decimal half = Math.Round(subtotal * 0.09m, 2);   // intra-state: CGST 9% + SGST 9%
            return (half, half, 0m);
        }
        return (0m, 0m, Math.Round(subtotal * 0.18m, 2));    // inter-state: IGST 18%
    }
}

// Responsibilities 2–4: behind interfaces so they can be swapped
public interface IInvoiceRepository { void Save(Invoice invoice); }
public interface IInvoiceSender     { void Send(Invoice invoice); }
public interface IAppLogger         { void Info(string message); }
""", "Billing/Invoice.cs")}
{C(r"""
namespace Billing;

public class CsvInvoiceRepository(string path) : IInvoiceRepository
{
    public void Save(Invoice i) =>
        File.AppendAllText(path, $"{i.Number},{i.CustomerEmail},{i.Total}{Environment.NewLine}");
}

public class ConsoleEmailSender : IInvoiceSender
{
    public void Send(Invoice i) =>
        Console.WriteLine($"[EMAIL] To {i.CustomerEmail}: invoice {i.Number}, total ₹{i.Total:N2}");
}

public class ConsoleLogger : IAppLogger
{
    public void Info(string message) => Console.WriteLine($"[INFO {DateTime.Now:HH:mm:ss}] {message}");
}

// The orchestrator: its only job is the workflow order
public class InvoiceService(GstCalculator gst, IInvoiceRepository repository, IInvoiceSender sender, IAppLogger log)
{
    private const string SellerState = "MH";
    private int _next = 1;

    public Invoice Create(string email, string buyerState, IReadOnlyList<InvoiceLine> lines)
    {
        if (lines.Count == 0) throw new ArgumentException("An invoice needs at least one line", nameof(lines));

        decimal subtotal = lines.Sum(l => l.Amount);
        var (cgst, sgst, igst) = gst.Calculate(subtotal, SellerState, buyerState);
        var invoice = new Invoice($"INV-{_next++:D5}", email, lines, subtotal, cgst, sgst, igst);

        repository.Save(invoice);
        sender.Send(invoice);
        log.Info($"Created {invoice.Number} for {email}");
        return invoice;
    }
}
""", "Billing/InvoiceService.cs")}
{C(r"""
using Billing;

var service = new InvoiceService(new GstCalculator(), new CsvInvoiceRepository("invoices.csv"),
                                 new ConsoleEmailSender(), new ConsoleLogger());

var inv = service.Create("asha@example.com", "KA",
    [new("Laptop bag", 1_499m, 2), new("Wireless mouse", 799m, 1)]);

Console.WriteLine($"Subtotal {inv.Subtotal:N2}  IGST {inv.Igst:N2}  Total {inv.Total:N2}");
// [EMAIL] To asha@example.com: invoice INV-00001, total ₹4,480.46
// [INFO 10:15:02] Created INV-00001 for asha@example.com
// Subtotal 3,797.00  IGST 683.46  Total 4,480.46

var local = new GstCalculator().Calculate(3_797m, "MH", "mh");
Console.WriteLine(local);   // (341.73, 341.73, 0)
""", "Program.cs")}
{tip("Test the split by asking \"who would request a change here?\" for each class. If the answer is one team or one rule set, the class has one responsibility.")}

<h3>4. Spotting SRP violations</h3>
{table(["Symptom","Likely split"],[
["Class name ends in Manager, Helper, Utils, Processor","Name each real job: Calculator, Repository, Sender, Validator"],
["Method has comment headings: // validate, // save, // notify","One collaborator per heading"],
["<code>using</code> list mixes System.IO, System.Net.Mail, Microsoft.Data.SqlClient","Infrastructure concerns behind interfaces"],
["You need a database to test a calculation","Extract the pure logic into its own class"],
["Fields used by only half the methods","Low cohesion: two classes hiding in one"]])}
{warn("Don't split by technical layer for its own sake. A 40-line class with one clear job is fine even if it has six methods. SRP is about cohesion, not size.", "Balance")}

<h3>5. OCP — before: a discount calculator with a growing switch</h3>
{C(r"""
public class DiscountCalculator
{
    public decimal Apply(string customerType, decimal amount)
    {
        switch (customerType)
        {
            case "Regular":  return amount;
            case "Silver":   return amount * 0.95m;
            case "Gold":     return amount * 0.90m;
            case "Employee": return amount * 0.70m;
            // Marketing: "add a festive sale"… edit here again
            // Product:   "first order gets ₹100 off"… and again
            default: throw new ArgumentException($"Unknown customer type {customerType}");
        }
    }
}
""", "Before/DiscountCalculator.cs")}
<p>Every new promotion means editing and re-testing this method, and the same <code>switch</code> tends to be copied into the cart page, the invoice and reports (shotgun surgery).</p>

<h3>6. OCP — after: rules as polymorphic objects</h3>
{C(r"""
namespace Pricing;

public record Order(string CustomerTier, decimal Amount, DateOnly Date, bool IsFirstOrder);
public record DiscountResult(string Rule, decimal Amount);

public interface IDiscountRule
{
    string Name { get; }
    bool AppliesTo(Order order);
    decimal DiscountFor(Order order);
}

public class TierDiscount(string tier, decimal percent) : IDiscountRule
{
    public string Name => $"{tier} {percent:0}%";
    public bool AppliesTo(Order o) => string.Equals(o.CustomerTier, tier, StringComparison.OrdinalIgnoreCase);
    public decimal DiscountFor(Order o) => Math.Round(o.Amount * percent / 100m, 2);
}

public class FirstOrderDiscount : IDiscountRule
{
    public string Name => "First order ₹100";
    public bool AppliesTo(Order o) => o.IsFirstOrder && o.Amount >= 500m;
    public decimal DiscountFor(Order o) => 100m;
}

public class FestiveDiscount(DateOnly from, DateOnly to, decimal percent) : IDiscountRule
{
    public string Name => $"Festive {percent:0}%";
    public bool AppliesTo(Order o) => o.Date >= from && o.Date <= to;
    public decimal DiscountFor(Order o) => Math.Round(o.Amount * percent / 100m, 2);
}

// Closed for modification: it never changes when a rule is added
public class DiscountCalculator(IEnumerable<IDiscountRule> rules)
{
    // Business policy: the single best discount wins (no stacking)
    public DiscountResult Best(Order order) =>
        rules.Where(r => r.AppliesTo(order))
             .Select(r => new DiscountResult(r.Name, r.DiscountFor(order)))
             .DefaultIfEmpty(new DiscountResult("None", 0m))
             .MaxBy(d => d.Amount)!;
}
""", "Pricing/Discounts.cs")}
{C(r"""
using Pricing;

IDiscountRule[] rules =
[
    new TierDiscount("Silver", 5), new TierDiscount("Gold", 10), new TierDiscount("Employee", 30),
    new FirstOrderDiscount(),
    new FestiveDiscount(new DateOnly(2026, 11, 1), new DateOnly(2026, 11, 15), 12)   // added without touching the calculator
];
var calc = new DiscountCalculator(rules);

Console.WriteLine(calc.Best(new Order("Gold", 2_000m, new DateOnly(2026, 10, 20), false)));
// DiscountResult { Rule = Gold 10%, Amount = 200 }
Console.WriteLine(calc.Best(new Order("Gold", 2_000m, new DateOnly(2026, 11, 10), false)));
// DiscountResult { Rule = Festive 12%, Amount = 240 }
Console.WriteLine(calc.Best(new Order("Regular", 600m, new DateOnly(2026, 12, 1), true)));
// DiscountResult { Rule = First order ₹100, Amount = 100 }
""", "Program.cs")}
<p>Adding a rule is now a new class plus one line where the rules are listed (later, one DI registration). The calculator and every existing rule stay untouched and keep their tests.</p>

<h4>Lighter-weight OCP: a dictionary of delegates</h4>
{C(r"""
// When variations are tiny, a lookup table of Func is enough (Week 5 lambdas)
var shippingByZone = new Dictionary<string, Func<decimal, decimal>>(StringComparer.OrdinalIgnoreCase)
{
    ["metro"]  = weightKg => 40m + 10m * Math.Ceiling(weightKg),
    ["rest"]   = weightKg => 60m + 15m * Math.Ceiling(weightKg),
    ["remote"] = weightKg => 120m + 25m * Math.Ceiling(weightKg)
};
Console.WriteLine(shippingByZone["Metro"](1.2m));   // 60  (40 + 10 × 2)
""")}
{table(["Situation","Prefer"],[
["Closed set that won't grow (DayOfWeek, a 3-state enum)","A <code>switch</code> expression — exhaustive and readable"],
["Growing list of business variations, each with logic","Interface + one class per variation"],
["Variations are one-liners with no state","Dictionary of <code>Func</code>"],
["Shared steps, one or two steps differ","Abstract base class with Template Method (Week 2)"]])}
''',
["Splitting a class into many tiny classes with no clear reason to change (fragmentation).",
"Thinking SRP means \"one method per class\".",
"Building plugin architectures for a variation that will never happen (violating YAGNI).",
"Keeping the switch but moving it into a \"factory\" that still has to be edited for every new rule, then calling it OCP.",
"Copying the same switch on customer type into several classes (shotgun surgery)."],
("40 min", ["Take the Week 3 bank's <code>Account</code> or a class of your own over 150 lines; list each reason to change and extract at least two collaborators.",
"Add a <code>WeekendDiscount</code> (5% on Saturday/Sunday) and a <code>BulkDiscount</code> (₹500 off above ₹20,000) without editing <code>DiscountCalculator</code>.",
"Change the policy to \"stack all discounts but cap at 40% of the amount\" by writing a second calculator class, and explain why the rules didn't change."]),
[("Does SRP mean a class should have only one method?","No. It means one reason to change. A class can have many methods as long as they all serve the same responsibility."),
("How do you know you're violating OCP?","When adding a new variant (a new customer tier, payment method, report type) forces you to edit existing, tested code, typically a switch or if-else chain."),
("Is every switch statement an OCP violation?","No. A switch over a closed, stable set is often the clearest code. It becomes a problem when the set grows with business requirements or the same switch is repeated.")],
[("Basic","What is the Single Responsibility Principle?","A class should have one reason to change: it serves one actor or concern. For example, GST calculation, invoice storage and email delivery change for different reasons and belong in different classes, coordinated by a thin service."),
("Basic","Explain the Open/Closed Principle with an example.","Code should be open for extension but closed for modification. A discount calculator that takes IEnumerable&lt;IDiscountRule&gt; lets you add a FestiveDiscount class without editing the calculator or existing rules, unlike a switch on customer type."),
("Basic","What do cohesion and coupling mean, and which do you want high?","Cohesion is how strongly a class's members relate to one purpose; coupling is how much it depends on other classes' details. Aim for high cohesion and low coupling."),
("Intermediate","How do you apply OCP without over-engineering?","Introduce an extension point when variation is real and recurring (rule of three), keep closed sets as switch expressions, and prefer the simplest mechanism that works: a delegate table before a class hierarchy, an interface before a plugin framework."),
("Intermediate","How does SRP make code easier to test?","Pure logic (GstCalculator) can be tested with plain inputs and outputs. Side effects (files, email, logging) sit behind interfaces, so the orchestrator can be tested with fakes that record calls instead of touching real infrastructure."),
("Intermediate","What is shotgun surgery and how do SOLID principles help?","A change that requires small edits in many classes, often because a switch on a type code is duplicated. Moving each variant's behaviour into its own polymorphic class (OCP) puts the change in one new place.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "SOLID part 2: Liskov, Interface Segregation, Dependency Inversion and DI",
"Design hierarchies that can be substituted safely, keep interfaces small, make business logic depend on abstractions, and wire it all together with constructor injection and a DI container.",
[("Liskov Substitution Principle (LSP)","Objects of a subtype must be usable anywhere the base type is expected without breaking correctness."),
("Precondition","What must be true before a method is called. A subtype may not strengthen it."),
("Postcondition","What a method guarantees afterwards. A subtype may not weaken it."),
("Invariant","A condition that is always true for an object (e.g. Balance ≥ 0). Subtypes must preserve it."),
("Interface Segregation Principle (ISP)","Clients shouldn't be forced to depend on methods they don't use; prefer small, role-based interfaces."),
("Fat interface","An interface with many unrelated members, forcing implementers to stub or throw."),
("Dependency Inversion Principle (DIP)","High-level policy and low-level details both depend on abstractions; the abstraction belongs to the policy side."),
("Dependency Injection (DI)","Giving an object its dependencies from outside instead of creating them inside."),
("Constructor injection","Passing required dependencies through the constructor; the default and preferred style."),
("Composition root","The single place (Program.cs) where concrete types are chosen and the object graph is assembled."),
("DI container","A library (Microsoft.Extensions.DependencyInjection) that builds object graphs from registrations."),
("Service lifetime","How long a container-created instance lives: Singleton, Scoped or Transient."),
("Captive dependency","A longer-lived service holding a shorter-lived one (a singleton holding a scoped DbContext), keeping it alive too long.")],
["LSP is about behaviour, not just compiling: \"is-a\" in the real world isn't enough.",
"If callers need <code>if (x is SomeSubtype)</code>, the hierarchy probably violates LSP.",
"ISP: split by client need. One class can still implement several small interfaces.",
"DIP: the business layer defines <code>IOrderStore</code>; the infrastructure layer implements it.",
"DI is the technique; DIP is the principle; a container is an optional tool.",
"Only Program.cs (the composition root) should call <code>new</code> on infrastructure classes or ask a container for services."],
f'''
<h3>1. LSP — the Rectangle/Square trap</h3>
{C(r"""
ResizeBanner(new Rectangle());    // 20
ResizeBanner(new Square());       // 16  ← substitution broke the caller's assumption

static void ResizeBanner(Rectangle r)
{
    r.Width = 5;
    r.Height = 4;
    Console.WriteLine(r.Area);    // the caller reasonably expects 20
}

public class Rectangle
{
    public virtual int Width  { get; set; }
    public virtual int Height { get; set; }
    public int Area => Width * Height;
}

// Mathematically a square IS a rectangle… behaviourally it isn't
public class Square : Rectangle
{
    public override int Width  { get => base.Width;  set { base.Width = value; base.Height = value; } }
    public override int Height { get => base.Height; set { base.Width = value; base.Height = value; } }
}
""", "LspBroken.cs")}
<p>The <code>Rectangle</code> setter's implicit postcondition is \"setting Width leaves Height unchanged\". <code>Square</code> weakens it. Fix it by not modelling mutable shapes as a hierarchy where they disagree; immutable types behind a common interface are safe:</p>
{C(r"""
IShape[] shapes = [new Rect(5, 4), new Sq(4)];
Console.WriteLine(shapes.Sum(s => s.Area));   // 36 — every IShape keeps its contract

public interface IShape { int Area { get; } }

public sealed record Rect(int Width, int Height) : IShape { public int Area => Width * Height; }
public sealed record Sq(int Side) : IShape              { public int Area => Side * Side; }
""", "LspFixed.cs")}

<h3>2. LSP in the BCL: read-only collections that throw</h3>
{C(r"""
using System.Collections.ObjectModel;

static void AddDefaultTag(ICollection<string> tags) => tags.Add("new-arrival");

AddDefaultTag(new List<string>());                          // ✓ fine
AddDefaultTag(new ReadOnlyCollection<string>(["sale"]));    // ❌ NotSupportedException
AddDefaultTag(new string[1]);                               // ❌ NotSupportedException: Collection was of a fixed size

// The "escape hatch" — callers must remember to check, which is the LSP smell
static void SafeAdd(ICollection<string> tags)
{
    if (tags.IsReadOnly) return;
    tags.Add("new-arrival");
}
""", "ReadOnlyLsp.cs")}
<p>Arrays implement <code>IList&lt;T&gt;</code> and <code>ReadOnlyCollection&lt;T&gt;</code> implements <code>ICollection&lt;T&gt;</code> for historical reasons, so the compiler accepts code that fails at runtime. That's why .NET added <code>IReadOnlyCollection&lt;T&gt;</code> and <code>IReadOnlyList&lt;T&gt;</code>: accept those when you only read, and <code>ICollection&lt;T&gt;</code> only when you genuinely add.</p>
{table(["Contract rule","A subtype may…","Example violation"],[
["Preconditions","not demand more (strengthen)","Base accepts any amount &gt; 0; subtype rejects amounts &lt; ₹100"],
["Postconditions","not promise less (weaken)","Base guarantees the order is saved; subtype silently skips saving"],
["Invariants","not break them","Base keeps Balance ≥ 0; subtype allows negative balance without an overdraft concept in the base"],
["Exceptions","not throw new, unexpected exception types","Override throws NotSupportedException or NotImplementedException"],
["History","not allow state changes the base forbids","An \"immutable\" base type gets a mutable subtype"]])}
{tip("In Week 3's bank, <code>Withdraw</code> worked for both account types because the base class defined the rule through <code>AvailableToWithdraw</code>. Overdraft wasn't a surprise exception; it was part of the base contract. That's LSP done right.")}

<h3>3. ISP — split fat interfaces by client</h3>
{C(r"""
public record Document(string Title, string Content);

// ❌ Fat interface: a basic printer must pretend it can scan and fax
public interface IOfficeDevice
{
    void Print(Document d);
    void Scan(Document d);
    void Fax(Document d, string number);
}

public class BasicInkjet : IOfficeDevice
{
    public void Print(Document d) => Console.WriteLine($"Printing {d.Title}");
    public void Scan(Document d) => throw new NotSupportedException();          // also an LSP violation
    public void Fax(Document d, string number) => throw new NotSupportedException();
}
""", "Before/IOfficeDevice.cs")}
{C(r"""
new PayslipService(new BasicInkjet()).PrintPayslip("Rohit Verma", 68_450m);          // Printing Payslip – Rohit Verma
new PayslipService(new OfficeMultiFunction()).PrintPayslip("Neha Joshi", 72_900m);   // [MFP] Printing Payslip – Neha Joshi

// ✓ Role interfaces (Document is the record from the "before" file)
public interface IPrinter { void Print(Document d); }
public interface IScanner { Document Scan(string title); }
public interface IFax     { void Fax(Document d, string number); }

public class BasicInkjet : IPrinter
{
    public void Print(Document d) => Console.WriteLine($"Printing {d.Title}");
}

public class OfficeMultiFunction : IPrinter, IScanner, IFax
{
    public void Print(Document d) => Console.WriteLine($"[MFP] Printing {d.Title}");
    public Document Scan(string title) => new(title, "(scanned image)");
    public void Fax(Document d, string number) => Console.WriteLine($"[MFP] Faxing {d.Title} to {number}");
}

// Each client asks only for the role it needs
public class PayslipService(IPrinter printer)
{
    public void PrintPayslip(string employee, decimal net) =>
        printer.Print(new Document($"Payslip – {employee}", $"Net pay ₹{net:N2}"));
}
""", "After/RoleInterfaces.cs")}
<p>The classic HR version: an <code>IWorker</code> with <code>Work()</code>, <code>TakeLunchBreak()</code> and <code>GetSalary()</code> forces a <code>RobotWorker</code> to implement lunch breaks. Split into <code>IWorkable</code>, <code>IFeedable</code>/<code>IHasBreaks</code> and <code>IPayable</code>.</p>

<h3>4. DIP — high-level policy depends on abstractions</h3>
{C(r"""
// ❌ Business rule glued to infrastructure: can't test without SQL and an SMS account
public class OrderServiceBefore
{
    private readonly SqlOrderStore _store = new("Server=.;Database=Shop;Trusted_Connection=True");
    private readonly SmsGatewayClient _sms = new("api-key");
    // Place(...) uses _store and _sms directly
}
""", "Before/OrderService.cs (fragment)")}
{C(r"""
namespace Shop.Core;            // the high-level project OWNS these abstractions

public record Order(int Id, string Customer, decimal Amount, DateTime PlacedAt);

public interface IOrderStore       { int NextId(); void Add(Order order); }
public interface ICustomerNotifier { void Notify(string customer, string message); }
public interface IClock            { DateTime Now { get; } }

public class OrderService(IOrderStore store, ICustomerNotifier notifier, IClock clock)
{
    public Order Place(string customer, decimal amount)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(customer);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(amount);

        var order = new Order(store.NextId(), customer, amount, clock.Now);
        store.Add(order);
        notifier.Notify(customer, $"Order #{order.Id} for ₹{amount:N2} confirmed");
        return order;
    }
}
""", "Shop.Core/OrderService.cs")}
{C(r"""
using Shop.Core;

namespace Shop.Infrastructure;  // low-level details depend UP on Shop.Core

public class InMemoryOrderStore : IOrderStore
{
    private readonly List<Order> _orders = [];
    public int NextId() => _orders.Count + 1001;
    public void Add(Order order) => _orders.Add(order);
}

public class ConsoleSmsNotifier : ICustomerNotifier
{
    public void Notify(string customer, string message) => Console.WriteLine($"[SMS → {customer}] {message}");
}

public class SystemClock : IClock { public DateTime Now => DateTime.Now; }
""", "Shop.Infrastructure/Implementations.cs")}
{table(["","Without DIP","With DIP"],[
["Project references","Core → Infrastructure","Infrastructure → Core"],
["Who defines <code>IOrderStore</code>","Nobody (concrete class used)","Shop.Core, in terms the business needs"],
["Swap SQL for an API","Edit OrderService","Write a new class implementing IOrderStore"],
["Unit test OrderService","Needs a database","Pass fakes"]])}

<h3>5. Dependency injection by hand: the composition root</h3>
{C(r"""
using Shop.Core;
using Shop.Infrastructure;

// Composition root: the ONLY place that knows the concrete classes
IClock clock = new SystemClock();
IOrderStore store = new InMemoryOrderStore();
ICustomerNotifier notifier = new ConsoleSmsNotifier();
var orders = new OrderService(store, notifier, clock);

orders.Place("Asha", 1_250m);    // [SMS → Asha] Order #1001 for ₹1,250.00 confirmed
orders.Place("Ravi", 640m);      // [SMS → Ravi] Order #1002 for ₹640.00 confirmed
""", "Shop.App/Program.cs")}
{table(["Injection style","How","Use for"],[
["Constructor","Parameters of the constructor (or primary constructor)","Required dependencies — the default"],
["Method","Passed to the one method that needs it","A dependency used by one operation, e.g. <code>CancellationToken</code>, <code>IFormatProvider</code>"],
["Property","Settable property with a sensible default","Truly optional dependencies; rare in .NET"]])}
<h4>Lifetimes, conceptually</h4>
{table(["Lifetime","One instance per…","Typical examples","Watch out"],[
["Singleton","Application","Configuration, clock, caches, HttpClient factory, stateless strategies","Must be thread-safe; must not hold scoped services"],
["Scoped","Scope (one HTTP request in ASP.NET Core)","EF Core DbContext, unit of work, current-user info","Don't resolve from the root provider"],
["Transient","Every resolve","Lightweight, stateless services, validators","Disposable transients live until their scope ends"]])}
{warn("A longer-lived service must not depend on a shorter-lived one. A singleton that receives a scoped DbContext keeps that one context forever — shared across requests and threads (a captive dependency).", "Rule")}

<h3>6. Preview: Microsoft.Extensions.DependencyInjection in a console app</h3>
{C(r"""
dotnet new console -n DiPreview
cd DiPreview
dotnet add package Microsoft.Extensions.DependencyInjection
""", lang="bash")}
{C(r"""
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddSingleton<SingletonTag>();
services.AddScoped<ScopedTag>();
services.AddTransient<TransientTag>();

using var provider = services.BuildServiceProvider(new ServiceProviderOptions
{
    ValidateScopes = true,     // throw if a scoped service is resolved from the root or captured by a singleton
    ValidateOnBuild = true     // check every registration can be constructed when building
});

for (int request = 1; request <= 2; request++)
{
    using var scope = provider.CreateScope();          // ≈ one web request
    var sp = scope.ServiceProvider;
    for (int resolve = 1; resolve <= 2; resolve++)
        Console.WriteLine($"request {request}, resolve {resolve}: " +
            $"singleton {sp.GetRequiredService<SingletonTag>().Id}  " +
            $"scoped {sp.GetRequiredService<ScopedTag>().Id}  " +
            $"transient {sp.GetRequiredService<TransientTag>().Id}");
}
// request 1, resolve 1: singleton 3f2a  scoped 91bc  transient 0d4e
// request 1, resolve 2: singleton 3f2a  scoped 91bc  transient 7a10
// request 2, resolve 1: singleton 3f2a  scoped c5e7  transient 22f9
// request 2, resolve 2: singleton 3f2a  scoped c5e7  transient b803
// (ids are random; the PATTERN of repeats is what matters)

public class SingletonTag { public string Id { get; } = Guid.NewGuid().ToString()[..4]; }
public class ScopedTag    { public string Id { get; } = Guid.NewGuid().ToString()[..4]; }
public class TransientTag { public string Id { get; } = Guid.NewGuid().ToString()[..4]; }
""", "DiPreview/Program.cs")}
<h4>Registering the shop with the container</h4>
{C(r"""
using Microsoft.Extensions.DependencyInjection;
using Shop.Core;
using Shop.Infrastructure;

var services = new ServiceCollection();
services.AddSingleton<IClock, SystemClock>();
services.AddScoped<IOrderStore, InMemoryOrderStore>();
services.AddTransient<ICustomerNotifier, ConsoleSmsNotifier>();
services.AddTransient<OrderService>();            // the container reads its constructor and supplies the three dependencies

using var provider = services.BuildServiceProvider(validateScopes: true);
using var scope = provider.CreateScope();
var orders = scope.ServiceProvider.GetRequiredService<OrderService>();
orders.Place("Meena", 2_100m);                    // [SMS → Meena] Order #1001 for ₹2,100.00 confirmed

// provider.GetRequiredService<OrderService>();   // ❌ with validateScopes: InvalidOperationException —
//                                                //    cannot resolve scoped IOrderStore from the root provider
""", "Program.cs (with container)")}
{tip("<code>GetRequiredService</code> throws a clear error if something isn't registered; <code>GetService</code> returns null. Outside the composition root you should almost never call either — that's the Service Locator anti-pattern. Let constructors declare what they need.")}
''',
["Inheriting just because \"X is a Y\" in English (Square/Rectangle, Ostrich/Bird with Fly()).",
"Overriding methods to throw <code>NotSupportedException</code> or <code>NotImplementedException</code>.",
"Defining interfaces in the infrastructure project, so the core still depends on infrastructure.",
"Calling <code>provider.GetService</code> from business classes (service locator) instead of constructor injection.",
"Registering a DbContext-like scoped service inside a singleton (captive dependency)."],
("40 min", ["Model <code>Bird</code>, <code>Sparrow</code> and <code>Penguin</code> so that no subtype throws from an inherited method. Hint: split <code>IFlyingBird</code> out.",
"Split a fat <code>IEmployeeService</code> (CalculateSalary, PrintIdCard, BookTravel, ApproveLeave) into role interfaces and write two clients that each depend on one role.",
"Rewire the Week 4 library app: build it once by hand in a composition root, then again with <code>ServiceCollection</code>; print singleton/scoped/transient ids to prove the lifetimes."]),
[("Why does Square violate LSP if it compiles fine?","LSP is behavioural. Code written against Rectangle assumes width and height change independently; Square breaks that postcondition, so substituting it changes the program's correctness."),
("Where should IOrderStore live: in Shop.Core or Shop.Infrastructure?","In Shop.Core, the high-level layer that uses it. Infrastructure references Core and implements the interface, so dependencies point toward the business logic."),
("What happens if you resolve a scoped service from the root provider?","With scope validation on it throws InvalidOperationException. Without validation it silently behaves like a singleton for the app's lifetime, a common source of bugs.")],
[("Basic","Explain the Liskov Substitution Principle.","If S is a subtype of T, any code that works with T must work correctly with S without knowing it. Subtypes may not strengthen preconditions, weaken postconditions, break invariants or throw unexpected exceptions."),
("Basic","What is the Interface Segregation Principle?","Prefer several small, client-specific interfaces over one large one, so implementers aren't forced to stub irrelevant members and clients aren't coupled to methods they don't use. Example: IPrinter, IScanner, IFax instead of IOfficeDevice."),
("Basic","What is the difference between DIP and DI?","DIP is a design principle: high-level modules and low-level modules both depend on abstractions owned by the high-level side. DI is a technique for supplying dependencies from outside (usually via constructors), which is how you achieve DIP in practice."),
("Intermediate","Explain Singleton, Scoped and Transient lifetimes.","Singleton: one instance for the application's lifetime. Scoped: one instance per scope, which in ASP.NET Core is one HTTP request. Transient: a new instance every time it's resolved. Choose by state and thread-safety: stateless and thread-safe can be singleton; per-request state like DbContext is scoped."),
("Intermediate","What is a captive dependency and how do you detect it?","A service with a longer lifetime holding one with a shorter lifetime, e.g. a singleton holding a scoped DbContext, which then lives forever and is shared across threads. Enable ValidateScopes (on by default in the Development environment in ASP.NET Core) and ValidateOnBuild to get exceptions."),
("Intermediate","What is a composition root and why have only one?","The single entry-point location, usually Program.cs, where the object graph is composed and concrete types are chosen. Keeping it in one place means the rest of the code depends only on abstractions and is easy to reconfigure or test.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Creational patterns: Singleton, Factories and Builder",
"Control how objects are created: guarantee a single instance safely, hide which concrete class gets created, and assemble complex objects step by step with a fluent builder.",
[("Design pattern","A named, reusable solution to a recurring design problem; vocabulary as much as code."),
("GoF","\"Gang of Four\": Gamma, Helm, Johnson and Vlissides, whose 1994 book catalogued 23 patterns in three groups."),
("Creational pattern","A pattern about how objects get created: Singleton, Factory Method, Abstract Factory, Builder, Prototype."),
("Singleton","Ensures a class has exactly one instance and provides global access to it."),
("Lazy&lt;T&gt;","A wrapper that creates its value on first access; thread-safe by default."),
("Static initialisation","The CLR runs a type's static initialisers exactly once, thread-safely."),
("Simple factory","A method or class that chooses and creates a concrete type from input (not a GoF pattern, but very common)."),
("Factory Method","A base class defines an abstract creation method; subclasses decide which concrete type to create."),
("Abstract Factory","An interface for creating families of related objects that must be used together."),
("Product","The object a factory creates, usually exposed through an interface."),
("Builder","Separates step-by-step construction of a complex object from its final representation."),
("Fluent interface","Methods that return <code>this</code> so calls can be chained."),
("Prototype","Creating new objects by copying an existing one; in C#, a record's <code>with</code> expression.")],
["Patterns are tools for specific problems; don't start a design by picking patterns.",
"In modern .NET, prefer a DI singleton over the hand-written Singleton pattern.",
"If you hand-write a singleton, use <code>Lazy&lt;T&gt;</code> or a static readonly field — never an unsynchronised null check.",
"A factory is worth it when creation logic is non-trivial or the concrete type depends on runtime input.",
"Use a builder when an object has many optional parts, ordering rules or validation that must run before it exists.",
"For simple objects, records with <code>required</code>/<code>init</code> properties beat a builder."],
f'''
<h3>1. Singleton — three implementations, one recommendation</h3>
{C(r"""
// ❌ 1. Naive: two threads can both see null and create two instances
public sealed class AppSettingsNaive
{
    private static AppSettingsNaive? _instance;
    private AppSettingsNaive() { }
    public static AppSettingsNaive Instance => _instance ??= new AppSettingsNaive();
}

// ✓ 2. Static readonly field: the CLR runs static initialisers once, thread-safely
public sealed class CurrencyFormatter
{
    public static readonly CurrencyFormatter Instance = new();
    private CurrencyFormatter() { }
    public string Format(decimal amount) => $"₹{amount:N2}";
}

// ✓ 3. Lazy<T>: thread-safe AND created only on first use
public sealed class GstRateTable
{
    private static readonly Lazy<GstRateTable> _instance = new(() => new GstRateTable());
    public static GstRateTable Instance => _instance.Value;

    private readonly Dictionary<string, decimal> _ratesByHsn;

    private GstRateTable()
    {
        Console.WriteLine("Loading GST rate table…");      // expensive work, runs once
        _ratesByHsn = new(StringComparer.Ordinal)
        {
            ["8471"] = 0.18m,   // computers (illustrative rates)
            ["0401"] = 0.00m,   // fresh milk
            ["3004"] = 0.05m    // medicines
        };
    }

    public decimal RateFor(string hsnCode) =>
        _ratesByHsn.TryGetValue(hsnCode, out var rate) ? rate : throw new KeyNotFoundException($"Unknown HSN {hsnCode}");
}
""", "Singletons.cs")}
{C(r"""
Parallel.For(0, 8, _ => GstRateTable.Instance.RateFor("8471"));
Console.WriteLine(ReferenceEquals(GstRateTable.Instance, GstRateTable.Instance));
// Loading GST rate table…      ← printed once, even with 8 threads
// True
""")}
<p><code>new Lazy&lt;T&gt;(factory)</code> uses <code>LazyThreadSafetyMode.ExecutionAndPublication</code> by default: only one thread runs the factory, the rest wait and get the same instance.</p>
<h4>Why DI singletons are preferred</h4>
{C(r"""
public interface IGstRates { decimal RateFor(string hsnCode); }

public sealed class GstRates : IGstRates           // ordinary class, public constructor, no static Instance
{
    public decimal RateFor(string hsnCode) => hsnCode == "8471" ? 0.18m : 0.05m;
}

// Composition root — the container guarantees one instance
services.AddSingleton<IGstRates, GstRates>();

// Consumers declare the dependency, so tests can pass a fake
public class InvoiceTaxService(IGstRates rates)
{
    public decimal TaxFor(string hsn, decimal amount) => Math.Round(amount * rates.RateFor(hsn), 2);
}
""", "DiSingleton.cs (fragment)")}
{table(["","Classic Singleton","DI singleton"],[
["Who enforces one instance","The class (private ctor + static)","The container registration"],
["Dependencies visible?","No — hidden <code>X.Instance</code> calls anywhere","Yes — in the constructor"],
["Unit testing","Hard: global state leaks between tests","Easy: inject a fake"],
["Swap implementation","Edit every caller","Change one registration"],
["Still useful for","Stateless helpers with no dependencies; library code with no container","Almost everything in an app"]])}

<h3>2. Simple factory</h3>
{C(r"""
// The customer's saved preference decides the concrete type at runtime
string preference = "WhatsApp";
NotificationSenderFactory.Create(preference).Send("+91 98450 12345", "Your order has shipped");
// [WHATSAPP +91 98450 12345] Your order has shipped

public interface INotificationSender
{
    string Channel { get; }
    void Send(string to, string message);
}

public class SmsSender : INotificationSender
{
    public string Channel => "sms";
    public void Send(string to, string message) => Console.WriteLine($"[SMS {to}] {message}");
}
public class EmailSender : INotificationSender
{
    public string Channel => "email";
    public void Send(string to, string message) => Console.WriteLine($"[EMAIL {to}] {message}");
}
public class WhatsAppSender : INotificationSender
{
    public string Channel => "whatsapp";
    public void Send(string to, string message) => Console.WriteLine($"[WHATSAPP {to}] {message}");
}

public static class NotificationSenderFactory
{
    public static INotificationSender Create(string channel) => channel.Trim().ToLowerInvariant() switch
    {
        "sms"      => new SmsSender(),
        "email"    => new EmailSender(),
        "whatsapp" => new WhatsAppSender(),
        _ => throw new ArgumentException($"Unknown channel '{channel}'", nameof(channel))
    };
}
""", "NotificationFactory.cs")}
<p>Callers no longer know the concrete classes. The factory still has a switch, but it is the <i>only</i> one. On Thursday you'll see how to remove it with shipping strategies: build a dictionary from all registered implementations (keyed by a <code>Key</code>/<code>Channel</code> property), so even the factory stops changing.</p>

<h3>3. Factory Method — let subclasses choose the product</h3>
{C(r"""
using System.Globalization;
using System.Text;

SalesRow[] rows = [new("Pune", 125_000m), new("Indore", 87_500m)];
ReportExporter exporter = new MarkdownExporter();
Console.Write(exporter.Export(rows));
// | City | Revenue |
// |---|---:|
// | Pune | ₹125,000 |
// | Indore | ₹87,500 |

public record SalesRow(string City, decimal Revenue);

public interface IReportFormatter
{
    string Header();
    string Row(SalesRow row);
}

public abstract class ReportExporter
{
    // The algorithm is fixed…
    public string Export(IReadOnlyList<SalesRow> rows)
    {
        IReportFormatter formatter = CreateFormatter();        // …but the product comes from the factory method
        var sb = new StringBuilder();
        sb.AppendLine(formatter.Header());
        foreach (var row in rows) sb.AppendLine(formatter.Row(row));
        return sb.ToString();
    }

    protected abstract IReportFormatter CreateFormatter();   // ← Factory Method
}

public class CsvExporter : ReportExporter
{
    protected override IReportFormatter CreateFormatter() => new CsvFormatter();

    private sealed class CsvFormatter : IReportFormatter
    {
        public string Header() => "City,Revenue";
        public string Row(SalesRow r) => $"{r.City},{r.Revenue.ToString(CultureInfo.InvariantCulture)}";
    }
}

public class MarkdownExporter : ReportExporter
{
    protected override IReportFormatter CreateFormatter() => new MarkdownFormatter();

    private sealed class MarkdownFormatter : IReportFormatter
    {
        public string Header() => "| City | Revenue |" + Environment.NewLine + "|---|---:|";
        public string Row(SalesRow r) => $"| {r.City} | ₹{r.Revenue:N0} |";
    }
}
""", "ReportExporter.cs")}
{tip("Factory Method is Template Method (Week 2) where the varying step is \"create an object\". You'll see it in ASP.NET Core too, e.g. overriding a method that creates a handler or a provider.")}

<h3>4. Abstract Factory — families that must match</h3>
<p>A payment provider has a charge API and a refund API. Mixing a sandbox gateway with a live refund service would be a disaster, so one factory creates the whole family.</p>
{C(r"""
// Chosen ONCE at startup
string environment = Environment.GetEnvironmentVariable("APP_ENV") ?? "Development";
IPaymentProviderFactory factory = environment == "Production"
    ? new LiveProviderFactory(Environment.GetEnvironmentVariable("PAY_API_KEY") ?? throw new InvalidOperationException("Missing key"))
    : new SandboxProviderFactory();

var gateway = factory.CreateGateway();
var refunds = factory.CreateRefunds();
string paymentId = gateway.Charge("ORD-1042", 1_499m);
Console.WriteLine(refunds.Refund(paymentId, 1_499m));   // sbx_rfnd_sbx_pay_ORD-1042

public interface IPaymentGateway { string Charge(string orderId, decimal amount); }
public interface IRefundGateway  { string Refund(string paymentId, decimal amount); }

public interface IPaymentProviderFactory
{
    IPaymentGateway CreateGateway();
    IRefundGateway CreateRefunds();
}

// Family 1: sandbox — fake ids, no money moves
public class SandboxProviderFactory : IPaymentProviderFactory
{
    public IPaymentGateway CreateGateway() => new SandboxGateway();
    public IRefundGateway CreateRefunds() => new SandboxRefunds();

    private sealed class SandboxGateway : IPaymentGateway
    {
        public string Charge(string orderId, decimal amount) => $"sbx_pay_{orderId}";
    }
    private sealed class SandboxRefunds : IRefundGateway
    {
        public string Refund(string paymentId, decimal amount) => $"sbx_rfnd_{paymentId}";
    }
}

// Family 2: live — would call the real provider's HTTP API
public class LiveProviderFactory(string apiKey) : IPaymentProviderFactory
{
    public IPaymentGateway CreateGateway() => new LiveGateway(apiKey);
    public IRefundGateway CreateRefunds() => new LiveRefunds(apiKey);

    private sealed class LiveGateway(string key) : IPaymentGateway
    {
        public string Charge(string orderId, decimal amount) => throw new NotImplementedException("HTTP call goes here");
    }
    private sealed class LiveRefunds(string key) : IRefundGateway
    {
        public string Refund(string paymentId, decimal amount) => throw new NotImplementedException("HTTP call goes here");
    }
}
""", "PaymentFactories.cs")}

<h3>5. Builder — fluent, validated construction</h3>
{C(r"""
using System.Text.RegularExpressions;

public sealed record OrderLine(string Sku, int Quantity, decimal UnitPrice);
public sealed record ShippingAddress(string Line1, string City, string Pin);

public sealed class Order
{
    public required string Customer { get; init; }
    public required IReadOnlyList<OrderLine> Lines { get; init; }
    public required ShippingAddress ShipTo { get; init; }
    public string? CouponCode { get; init; }
    public bool GiftWrap { get; init; }
    public decimal Total => Lines.Sum(l => l.Quantity * l.UnitPrice);
}

public sealed class OrderBuilder
{
    private static readonly Regex PinFormat = new(@"^[1-9]\d{5}$");   // Indian PIN: 6 digits, no leading 0

    private string? _customer;
    private readonly List<OrderLine> _lines = [];
    private ShippingAddress? _address;
    private string? _coupon;
    private bool _giftWrap;

    public OrderBuilder For(string customer) { _customer = customer.Trim(); return this; }

    public OrderBuilder Add(string sku, int quantity, decimal unitPrice)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(quantity);
        ArgumentOutOfRangeException.ThrowIfNegative(unitPrice);
        _lines.Add(new OrderLine(sku, quantity, unitPrice));
        return this;
    }

    public OrderBuilder ShipTo(string line1, string city, string pin) { _address = new(line1, city, pin); return this; }
    public OrderBuilder WithCoupon(string code) { _coupon = code.Trim().ToUpperInvariant(); return this; }
    public OrderBuilder AsGift() { _giftWrap = true; return this; }

    public Order Build()
    {
        if (string.IsNullOrWhiteSpace(_customer)) throw new InvalidOperationException("Customer is required");
        if (_lines.Count == 0) throw new InvalidOperationException("Add at least one line");
        if (_address is null) throw new InvalidOperationException("Shipping address is required");
        if (!PinFormat.IsMatch(_address.Pin)) throw new InvalidOperationException($"Invalid PIN code {_address.Pin}");

        return new Order
        {
            Customer = _customer,
            Lines = _lines.ToList(),          // copy: later builder calls can't change this order
            ShipTo = _address,
            CouponCode = _coupon,
            GiftWrap = _giftWrap
        };
    }
}
""", "OrderBuilder.cs")}
{C(r"""
var order = new OrderBuilder()
    .For("Kavya Iyer")
    .Add("SKU-KURTA", 2, 899m)
    .Add("SKU-DUPATTA", 1, 499m)
    .ShipTo("12 MG Road", "Bengaluru", "560001")
    .WithCoupon("diwali10")
    .AsGift()
    .Build();

Console.WriteLine($"{order.Customer}: {order.Lines.Count} lines, ₹{order.Total:N2}, coupon {order.CouponCode}, gift {order.GiftWrap}");
// Kavya Iyer: 2 lines, ₹2,297.00, coupon DIWALI10, gift True

new OrderBuilder().For("Ravi").Add("SKU-PEN", 1, 20m).ShipTo("1 Main St", "Chennai", "060001").Build();
// ❌ InvalidOperationException: Invalid PIN code 060001
""")}
<h4>Builders you already use in .NET</h4>
{C(r"""
var sb = new StringBuilder().Append("INV-").Append(2026).Append('-').Append(42);   // fluent, then ToString()

var uri = new UriBuilder("https", "api.example.in") { Path = "orders", Query = "status=open" }.Uri;

var builder = WebApplication.CreateBuilder(args);       // configure step by step…
builder.Services.AddSingleton<IGstRates, GstRates>();   // …services
builder.Configuration.AddJsonFile("tax.json", optional: true);
var app = builder.Build();                              // …then build the immutable app
""", "BuildersInDotNet.cs (fragment)")}

<h3>6. Choosing a creational pattern</h3>
{table(["Problem","Pattern",".NET-flavoured alternative"],[
["Exactly one shared instance","Singleton","<code>services.AddSingleton&lt;T&gt;()</code>"],
["Concrete type depends on runtime input","Simple factory","Dictionary of registered implementations; keyed services (.NET 8)"],
["Base class workflow, subclass picks the product","Factory Method","Inject the product or a <code>Func&lt;T&gt;</code>"],
["Related objects must come from the same family","Abstract Factory","Register the family per environment in DI"],
["Many optional parts, validation before existence","Builder","Records with <code>required</code> for simple cases"],
["Copy an existing object with small changes","Prototype","<code>record with { ... }</code>"]])}
''',
["Writing a Singleton with an unsynchronised null check.",
"Using Singletons as global mutable state (<code>AppState.Instance.CurrentUser</code>) — hidden coupling and test pollution.",
"Creating a factory for a type that has one implementation and a trivial constructor.",
"A builder whose <code>Build()</code> doesn't validate, so invalid objects still escape.",
"Returning the builder's internal list from <code>Build()</code>, so later builder calls mutate a built object."],
("35 min", ["Write a thread-safe <code>Lazy&lt;T&gt;</code> singleton <code>StateCodeTable</code> (KA → Karnataka…) and prove with <code>Parallel.For</code> that the constructor runs once; then convert it to a DI singleton behind an interface.",
"Create an <code>ExporterFactory</code> that returns a <code>ReportExporter</code> for \"csv\", \"md\" or \"html\"; add an <code>HtmlExporter</code> with its own Factory Method.",
"Write a fluent <code>HttpRequestBuilder</code> (<code>Get/Post</code>, <code>WithHeader</code>, <code>WithBearerToken</code>, <code>WithJsonBody</code>) whose <code>Build()</code> returns an <code>HttpRequestMessage</code> and rejects a body on GET."]),
[("Why is the naive <code>??=</code> singleton unsafe?","Two threads can both read null before either assigns, so both construct an instance and one overwrites the other; any state in the first is lost."),
("What is the difference between Factory Method and Abstract Factory?","Factory Method is one overridable creation method used inside a base class's algorithm. Abstract Factory is an object with several creation methods producing a family of related products that must be used together."),
("When is a builder overkill?","When the object has a few required properties and no cross-field validation. A record or class with <code>required</code>/<code>init</code> properties and an object initialiser is clearer.")],
[("Basic","What is the Singleton pattern and how do you implement it thread-safely in C#?","It ensures one instance with global access. In C# use a private constructor plus either <code>static readonly T Instance = new()</code> or <code>static readonly Lazy&lt;T&gt;</code>, which is thread-safe by default (ExecutionAndPublication). Avoid unsynchronised null checks."),
("Basic","Why are DI-registered singletons preferred over the classic Singleton?","Dependencies become explicit in constructors, implementations can be swapped or faked in tests, the class has no static global state, and lifetime is a configuration decision in one place instead of baked into the class."),
("Basic","What problem does the Builder pattern solve?","Constructing complex objects with many optional parts or ordering and validation rules, without telescoping constructors. A fluent builder collects parts step by step and validates in Build(). StringBuilder and WebApplicationBuilder are .NET examples."),
("Intermediate","Explain Factory Method with an example.","A base class defines an algorithm that needs an object but declares an abstract method to create it; subclasses override that method to choose the concrete type. ReportExporter.Export uses CreateFormatter(), which CsvExporter and MarkdownExporter override."),
("Intermediate","When would you use an Abstract Factory?","When several related objects must be consistent with each other, such as a payment provider's charge and refund clients for sandbox vs live, or UI widgets for one theme. Choosing the factory once guarantees you never mix families."),
("Intermediate","Is Singleton an anti-pattern?","The hand-written version often is in application code: it hides dependencies, introduces global mutable state and makes testing hard. A single instance per app is still often right; just let the DI container manage that lifetime.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Behavioural and data patterns: Strategy, Observer, Repository and Unit of Work",
"Swap algorithms at runtime with Strategy, let objects react to changes with Observer, and keep data access behind repositories coordinated by a unit of work.",
[("Behavioural pattern","A pattern about how objects interact and share responsibilities: Strategy, Observer, Command, State, Chain of Responsibility…"),
("Strategy","A family of interchangeable algorithms behind one interface, chosen at runtime by the client."),
("Context","The class that uses a strategy without knowing which concrete one it has."),
("Keyed service",".NET 8 DI feature: register several implementations of one interface under keys and resolve by key."),
("Observer","A subject notifies a list of dependents (observers) when its state changes, without knowing what they do."),
("Subject / publisher","The object that raises notifications (an event source)."),
("Subscriber / observer","An object or handler that registers to be notified."),
("IObservable&lt;T&gt; / IObserver&lt;T&gt;","BCL interfaces for push-based streams: Subscribe returns IDisposable; observers get OnNext, OnError, OnCompleted."),
("Rx (Reactive Extensions)","The System.Reactive library: LINQ-style operators over IObservable&lt;T&gt; (Where, Throttle, Buffer…)."),
("Repository","Collection-like abstraction over storage for one aggregate/entity type (Week 4)."),
("Unit of Work","Tracks changes made during a business transaction and commits them together, all or nothing."),
("Aggregate","A cluster of objects treated as one unit for changes, e.g. an Order with its lines."),
("Persistence ignorance","Domain classes that don't know how or where they're stored.")],
["Strategy replaces <code>if/switch</code> on \"which algorithm\" with polymorphism chosen at runtime.",
"Inject <code>IEnumerable&lt;IStrategy&gt;</code> and index it by a key, or use .NET 8 keyed services.",
"C# events are the built-in Observer pattern; use them for in-process notifications.",
"<code>IObservable&lt;T&gt;</code> fits streams of values over time (prices, sensor readings) and composes with Rx.",
"Always unsubscribe (or dispose the subscription) when the observer lives shorter than the subject.",
"EF Core's <code>DbContext</code> already is a Unit of Work, and each <code>DbSet&lt;T&gt;</code> is a repository."],
f'''
<h3>1. Strategy — interchangeable shipping algorithms</h3>
{C(r"""
namespace Checkout;

public record Parcel(decimal WeightKg, string FromPin, string ToPin, decimal OrderValue);

public interface IShippingStrategy
{
    string Key { get; }
    bool IsAvailable(Parcel p);
    decimal Cost(Parcel p);
    int Days(Parcel p);
}

internal static class Pin
{
    public static bool SameRegion(Parcel p)   => p.FromPin[0] == p.ToPin[0];          // first digit: postal region
    public static bool SameDistrict(Parcel p) => p.FromPin[..3] == p.ToPin[..3];      // first 3: sorting district
}

public class StandardShipping : IShippingStrategy
{
    public string Key => "standard";
    public bool IsAvailable(Parcel p) => true;
    public decimal Cost(Parcel p) => p.OrderValue >= 499m ? 0m : 40m + 10m * Math.Ceiling(p.WeightKg);
    public int Days(Parcel p) => Pin.SameRegion(p) ? 3 : 6;
}

public class ExpressShipping : IShippingStrategy
{
    public string Key => "express";
    public bool IsAvailable(Parcel p) => p.WeightKg <= 20m;
    public decimal Cost(Parcel p) => 99m + 20m * Math.Ceiling(p.WeightKg);
    public int Days(Parcel p) => Pin.SameRegion(p) ? 1 : 3;
}

public class SameDayShipping : IShippingStrategy
{
    public string Key => "sameday";
    public bool IsAvailable(Parcel p) => Pin.SameDistrict(p) && p.WeightKg <= 5m;
    public decimal Cost(Parcel p) => 149m;
    public int Days(Parcel p) => 0;
}
""", "Checkout/ShippingStrategies.cs")}
<h4>The context: selecting a strategy via a dictionary</h4>
{C(r"""
namespace Checkout;

public class ShippingQuoteService
{
    private readonly Dictionary<string, IShippingStrategy> _byKey;

    // Every registered strategy arrives here; adding one needs no change to this class
    public ShippingQuoteService(IEnumerable<IShippingStrategy> strategies) =>
        _byKey = strategies.ToDictionary(s => s.Key, StringComparer.OrdinalIgnoreCase);   // throws on duplicate keys — good

    public decimal Quote(string key, Parcel parcel)
    {
        if (!_byKey.TryGetValue(key, out var strategy))
            throw new ArgumentException($"Unknown shipping option '{key}'", nameof(key));
        if (!strategy.IsAvailable(parcel))
            throw new InvalidOperationException($"'{key}' isn't available for this parcel");
        return strategy.Cost(parcel);
    }

    public IReadOnlyList<(string Key, decimal Cost, int Days)> Options(Parcel parcel) =>
        _byKey.Values.Where(s => s.IsAvailable(parcel))
                     .Select(s => (s.Key, s.Cost(parcel), s.Days(parcel)))
                     .OrderBy(o => o.Item2)
                     .ToList();
}
""", "Checkout/ShippingQuoteService.cs")}
{C(r"""
using Checkout;

var quotes = new ShippingQuoteService([new StandardShipping(), new ExpressShipping(), new SameDayShipping()]);

var puneToPune = new Parcel(1.2m, "411001", "411038", 650m);
foreach (var (key, cost, days) in quotes.Options(puneToPune))
    Console.WriteLine($"{key,-9} ₹{cost,6:N2}  {days} day(s)");
// standard  ₹  0.00  3 day(s)
// express   ₹139.00  1 day(s)
// sameday   ₹149.00  0 day(s)

var puneToDelhi = puneToPune with { ToPin = "110001" };
Console.WriteLine(quotes.Options(puneToDelhi).Count);     // 2 — same-day isn't offered
""", "Program.cs")}
<h4>Registering strategies with DI</h4>
{C(r"""
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddSingleton<IShippingStrategy, StandardShipping>();     // several registrations of ONE interface
services.AddSingleton<IShippingStrategy, ExpressShipping>();
services.AddSingleton<IShippingStrategy, SameDayShipping>();
services.AddSingleton<ShippingQuoteService>();                   // receives IEnumerable<IShippingStrategy> with all three

// .NET 8 keyed services: resolve one implementation by key
services.AddKeyedSingleton<IShippingStrategy, ExpressShipping>("express");

using var provider = services.BuildServiceProvider();
var express = provider.GetRequiredKeyedService<IShippingStrategy>("express");

// …or inject by key: public class PrimeCheckout([FromKeyedServices("express")] IShippingStrategy shipping) { }
""", "Program.cs (DI)")}
{tip("Resolving a single <code>IShippingStrategy</code> when several are registered gives you the <b>last</b> registration. Inject <code>IEnumerable&lt;IShippingStrategy&gt;</code> to get all of them, in registration order.")}

<h3>2. Observer with C# events</h3>
<p>You built events in Week 3's bank. In pattern language, the account was the <i>subject</i> and the console handlers were <i>observers</i>.</p>
{C(r"""
var tracker = new OrderTracker();
var sms = new SmsNotifier();
tracker.StatusChanged += sms.OnStatusChanged;
tracker.StatusChanged += (_, e) =>                         // observer 2: analytics
{
    if (e.Status == OrderStatus.Delivered) Console.WriteLine($"[Analytics] delivered #{e.OrderId}");
};

tracker.Update(1042, OrderStatus.Shipped);      // [SMS] Order #1042 is now Shipped
tracker.Update(1042, OrderStatus.Shipped);      // (nothing — unchanged)
tracker.StatusChanged -= sms.OnStatusChanged;   // unsubscribe
tracker.Update(1042, OrderStatus.Delivered);    // [Analytics] delivered #1042

public enum OrderStatus { Placed, Packed, Shipped, Delivered }

public class OrderStatusChangedEventArgs(int orderId, OrderStatus status) : EventArgs
{
    public int OrderId { get; } = orderId;
    public OrderStatus Status { get; } = status;
}

public class OrderTracker                                  // subject
{
    private readonly Dictionary<int, OrderStatus> _status = new();
    public event EventHandler<OrderStatusChangedEventArgs>? StatusChanged;

    public void Update(int orderId, OrderStatus status)
    {
        if (_status.TryGetValue(orderId, out var old) && old == status) return;   // no change, no noise
        _status[orderId] = status;
        StatusChanged?.Invoke(this, new(orderId, status));
    }
}

public class SmsNotifier                                   // observer 1
{
    public void OnStatusChanged(object? sender, OrderStatusChangedEventArgs e) =>
        Console.WriteLine($"[SMS] Order #{e.OrderId} is now {e.Status}");
}
""", "OrderTracker.cs")}

<h3>3. IObservable&lt;T&gt; — streams of values</h3>
{C(r"""
var feed = new StockPriceFeed();
using (feed.Subscribe(new PriceAlert("INFRA", 2_500m)))
{
    feed.Publish(2_480m);      // (below threshold)
    feed.Publish(2_515m);      // INFRA at ₹2515 crossed ₹2500
}
feed.Publish(2_600m);          // nothing — subscription disposed

public sealed class StockPriceFeed : IObservable<decimal>
{
    private readonly List<IObserver<decimal>> _observers = [];

    public IDisposable Subscribe(IObserver<decimal> observer)
    {
        _observers.Add(observer);
        return new Subscription(_observers, observer);       // disposing it unsubscribes
    }

    public void Publish(decimal price)
    {
        foreach (var o in _observers.ToList()) o.OnNext(price);   // copy: observers may unsubscribe while we loop
    }

    public void Close()
    {
        foreach (var o in _observers.ToList()) o.OnCompleted();
        _observers.Clear();
    }

    private sealed class Subscription(List<IObserver<decimal>> list, IObserver<decimal> observer) : IDisposable
    {
        public void Dispose() => list.Remove(observer);
    }
}

public sealed class PriceAlert(string symbol, decimal threshold) : IObserver<decimal>
{
    public void OnNext(decimal price)
    {
        if (price >= threshold) Console.WriteLine($"{symbol} at ₹{price} crossed ₹{threshold}");
    }
    public void OnError(Exception error) => Console.WriteLine($"{symbol} feed error: {error.Message}");
    public void OnCompleted() => Console.WriteLine($"{symbol} feed closed");
}
""", "PriceFeed.cs")}
{table(["","C# events","IObservable&lt;T&gt;"],[
["Shape","Discrete notifications (\"status changed\")","A stream of values over time, with completion and error"],
["Unsubscribe","<code>-=</code> with the same delegate","Dispose the IDisposable from Subscribe"],
["Completion / error signals","No (you'd add more events)","OnCompleted, OnError"],
["Composition","Manual","Rx operators: Where, Select, Throttle, Buffer, CombineLatest"],
["Pass around as a value","Awkward","Natural — it's just an object"],
["Typical use","UI, domain notifications, in-process alerts","Market data, telemetry, sensor feeds, SignalR streams"]])}
<p class="muted">The BCL ships only the two interfaces. For real work install <code>System.Reactive</code>, which provides <code>Subject&lt;T&gt;</code> and LINQ-style operators.</p>

<h3>4. Repository recap</h3>
<p>In Week 4 you hid the library's storage behind <code>IRepository&lt;T&gt;</code>. The essential ideas:</p>
{C(r"""
public interface IEntity { int Id { get; } }

public interface IRepository<T> where T : class, IEntity
{
    T? GetById(int id);
    IReadOnlyList<T> GetAll();
    void Add(T entity);
    void Remove(T entity);
}

// A specific repository adds queries that speak the domain's language
public interface IOrderRepository : IRepository<Order>
{
    IReadOnlyList<Order> PendingFor(string customer);
}
""", "Repositories.cs (fragment)")}
{table(["Benefit","Cost"],[
["Business code doesn't know about SQL, files or HTTP","Another layer to maintain"],
["Easy to fake in unit tests","Generic repositories over EF Core can hide useful features (Include, projections)"],
["One place for query logic per aggregate","Risk of \"one repository per table\" instead of per aggregate"]])}

<h3>5. Unit of Work — commit several changes together</h3>
<p>Placing an order writes an <code>Order</code> and a <code>Payment</code>. If the payment save fails after the order is saved, the data is inconsistent. A unit of work collects changes from several repositories and commits them in one step.</p>
{C(r"""
public record Order(int Id, string Customer, decimal Amount) : IEntity;
public record Payment(int Id, int OrderId, decimal Amount) : IEntity;

public interface IUnitOfWork
{
    IRepository<Order> Orders { get; }
    IRepository<Payment> Payments { get; }
    int SaveChanges();                                   // all or nothing
}

public sealed class StagedRepository<T> : IRepository<T> where T : class, IEntity
{
    private readonly Dictionary<int, T> _committed = new();
    private readonly List<T> _toAdd = [];
    private readonly List<T> _toRemove = [];

    public T? GetById(int id) => _committed.GetValueOrDefault(id) ?? _toAdd.FirstOrDefault(e => e.Id == id);
    public IReadOnlyList<T> GetAll() => _committed.Values.ToList();
    public void Add(T entity) => _toAdd.Add(entity);         // staged, not saved
    public void Remove(T entity) => _toRemove.Add(entity);

    internal bool HasConflict(out string? error)
    {
        foreach (var e in _toAdd)
            if (_committed.ContainsKey(e.Id)) { error = $"{typeof(T).Name} {e.Id} already exists"; return true; }
        error = null;
        return false;
    }

    internal int Commit()
    {
        foreach (var e in _toAdd) _committed.Add(e.Id, e);
        foreach (var e in _toRemove) _committed.Remove(e.Id);
        int changes = _toAdd.Count + _toRemove.Count;
        Discard();
        return changes;
    }

    internal void Discard() { _toAdd.Clear(); _toRemove.Clear(); }
}

public sealed class InMemoryUnitOfWork : IUnitOfWork
{
    private readonly StagedRepository<Order> _orders = new();
    private readonly StagedRepository<Payment> _payments = new();
    public IRepository<Order> Orders => _orders;
    public IRepository<Payment> Payments => _payments;

    public int SaveChanges()
    {
        // Validate EVERYTHING before applying ANYTHING
        if (_orders.HasConflict(out var error) || _payments.HasConflict(out error))
        {
            _orders.Discard();
            _payments.Discard();
            throw new InvalidOperationException($"Nothing saved: {error}");
        }
        return _orders.Commit() + _payments.Commit();
    }
}
""", "UnitOfWork.cs")}
{C(r"""
var uow = new InMemoryUnitOfWork();
var checkout = new CheckoutService(uow);
checkout.PlaceOrder(1, "Asha", 1_200m);
Console.WriteLine($"{uow.Orders.GetAll().Count} order, {uow.Payments.GetAll().Count} payment");   // 1 order, 1 payment

try { checkout.PlaceOrder(1, "Ravi", 900m); }                // duplicate order id
catch (InvalidOperationException ex) { Console.WriteLine(ex.Message); }   // Nothing saved: Order 1 already exists
Console.WriteLine(uow.Payments.GetAll().Count);               // 1 — Ravi's payment wasn't saved either

public class CheckoutService(IUnitOfWork uow)
{
    public void PlaceOrder(int orderId, string customer, decimal amount)
    {
        uow.Orders.Add(new Order(orderId, customer, amount));
        uow.Payments.Add(new Payment(orderId * 10, orderId, amount));
        uow.SaveChanges();                                   // one commit for both
    }
}
""", "Program.cs")}
{table(["Concept","EF Core equivalent (Weeks 14–16)"],[
["Repository","<code>DbSet&lt;Order&gt;</code>"],
["Unit of Work","<code>DbContext</code> (change tracker)"],
["Staged Add/Remove","<code>Add</code>, <code>Remove</code>, tracked property changes"],
["SaveChanges (all or nothing)","<code>SaveChanges()</code> runs inside a database transaction"],
["Scoped per request","<code>AddDbContext</code> registers it as Scoped"]])}
''',
["Choosing a strategy with a switch inside the context, which defeats the purpose.",
"Resolving a single interface when several implementations are registered and silently getting the last one.",
"Subscribing to a long-lived event from a short-lived object and never unsubscribing (memory leak, Week 3).",
"Iterating the observer list while a callback unsubscribes, causing \"Collection was modified\".",
"Calling SaveChanges inside each repository method, so related changes can't be committed together."],
("40 min", ["Implement payment strategies <code>UpiPayment</code>, <code>CardPayment</code> (2% fee) and <code>CashOnDelivery</code> (₹40 fee, max ₹10,000) behind <code>IPaymentStrategy</code> and select one by key from a dictionary.",
"Add a <code>WarehouseObserver</code> to <code>OrderTracker</code> that only reacts to <code>Packed</code>, and make <code>Update</code> ignore backwards transitions (Delivered → Shipped).",
"Extend <code>InMemoryUnitOfWork</code> with a <code>Customers</code> repository and prove that a failure in any of the three repositories saves nothing."]),
[("How does Strategy differ from a switch on algorithm type?","Each algorithm lives in its own class behind one interface, and the context receives the one it needs. Adding an algorithm adds a class instead of editing the context."),
("What does disposing the IDisposable returned by Subscribe do?","It removes that observer from the subject so it stops receiving OnNext calls. It's the IObservable equivalent of <code>-=</code>."),
("Why does a unit of work help consistency?","It collects all changes of one business operation and commits them in a single step after validation (in EF Core, inside one transaction), so you never persist half of the operation.")],
[("Basic","What is the Strategy pattern? Give a real example.","A family of interchangeable algorithms behind a common interface, selected at runtime. Shipping options (standard, express, same-day) or payment methods each implement IShippingStrategy/IPaymentStrategy, and checkout uses whichever the customer chooses."),
("Basic","How are C# events related to the Observer pattern?","An event is a built-in implementation of Observer: the publisher keeps a multicast delegate list, subscribers add handlers with +=, and the publisher invokes them when something happens, without knowing who they are."),
("Basic","What is the Repository pattern?","An abstraction that exposes collection-like operations for an entity or aggregate and hides how data is stored, so business logic doesn't depend on the database and can be tested with in-memory fakes."),
("Intermediate","How do you register and resolve multiple implementations of one interface in .NET DI?","Register each with the same service type; inject IEnumerable&lt;T&gt; to receive all in registration order (often converted to a dictionary by key). Resolving T alone returns the last registration. In .NET 8+ you can also use keyed services: AddKeyedSingleton and [FromKeyedServices(key)]."),
("Intermediate","Events vs IObservable&lt;T&gt;: when would you choose each?","Events for simple in-process notifications tied to an object. IObservable for streams of values over time that need completion/error signals, can be passed around as objects, and benefit from Rx operators like Throttle or Buffer."),
("Intermediate","Is a separate Unit of Work needed with EF Core?","Usually not: DbContext is already a unit of work and DbSet a repository. Teams add an IUnitOfWork wrapper mainly to keep the domain independent of EF Core or to coordinate several contexts, accepting the extra abstraction cost.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Structural patterns: Decorator, Adapter, and patterns inside .NET",
"Add behaviour such as caching and logging without touching the original class, wrap third-party SDKs behind your own interfaces, and recognise the patterns the .NET libraries are built from.",
[("Structural pattern","A pattern about composing classes and objects into larger structures: Decorator, Adapter, Facade, Composite, Proxy."),
("Decorator","Wraps an object that implements an interface with another implementation of the same interface, adding behaviour before/after delegating."),
("Wrapper / inner","The decorator holds a reference to the inner (decorated) object and forwards calls to it."),
("Cross-cutting concern","Behaviour needed in many places but unrelated to business logic: logging, caching, retries, metrics, authorisation."),
("Adapter","Converts the interface of an existing class (often third-party) into the interface your code expects."),
("Adaptee","The class being adapted, e.g. a vendor SDK client."),
("Anti-corruption layer","A boundary of adapters that keeps a third-party model from leaking into your domain."),
("Facade","A simple interface over a complex subsystem."),
("Proxy","Same interface as the real object, controlling access to it (lazy loading, remote calls, permissions)."),
("Chain of Responsibility","A request passes along a chain of handlers; each can handle it, modify it or pass it on."),
("Iterator","Sequential access to elements without exposing the underlying structure: IEnumerable/IEnumerator."),
("TimeProvider",".NET 8 abstraction over the system clock, useful for testable expiry logic.")],
["Decorator and the wrapped class implement the <b>same</b> interface; callers can't tell the difference.",
"Decorators stack: order matters (logging outside caching logs hits and misses; inside it logs only misses).",
"Adapter changes the <b>shape</b> of an API; Decorator keeps the shape and adds behaviour.",
"Wrap every third-party SDK behind an interface you own; your domain should never reference vendor types.",
"Many .NET APIs are patterns: Stream wrappers (Decorator), middleware and HttpClient handlers (Chain of Responsibility), IEnumerable (Iterator).",
"In ASP.NET Core you'll register decorators with a factory lambda or the Scrutor library's <code>Decorate</code>."],
f'''
<h3>1. Decorator — caching and timing around a catalogue</h3>
{C(r"""
using System.Diagnostics;

namespace Catalog;

public record Product(string Sku, string Name, decimal Price);

public interface IProductCatalog
{
    Product? GetBySku(string sku);
}

// The real implementation: slow, like a database round-trip
public sealed class DbProductCatalog : IProductCatalog
{
    private readonly Dictionary<string, Product> _rows = new(StringComparer.OrdinalIgnoreCase)
    {
        ["SKU-TEA"]  = new("SKU-TEA", "Assam tea 500 g", 245m),
        ["SKU-GHEE"] = new("SKU-GHEE", "Desi ghee 1 L", 650m)
    };
    public int Queries { get; private set; }

    public Product? GetBySku(string sku)
    {
        Queries++;
        Thread.Sleep(200);                                // simulate latency
        return _rows.GetValueOrDefault(sku);
    }
}

// Decorator 1: caching (same interface, wraps an inner catalogue)
public sealed class CachingProductCatalog(IProductCatalog inner, TimeProvider time, TimeSpan ttl) : IProductCatalog
{
    private readonly Dictionary<string, (Product? Product, DateTimeOffset Expires)> _cache = new(StringComparer.OrdinalIgnoreCase);

    public Product? GetBySku(string sku)
    {
        var now = time.GetUtcNow();
        if (_cache.TryGetValue(sku, out var entry) && entry.Expires > now)
            return entry.Product;                         // hit: inner never called

        var product = inner.GetBySku(sku);                // miss: delegate
        _cache[sku] = (product, now + ttl);
        return product;
    }
}

// Decorator 2: timing/logging
public sealed class TimedProductCatalog(IProductCatalog inner) : IProductCatalog
{
    public Product? GetBySku(string sku)
    {
        var sw = Stopwatch.StartNew();
        var product = inner.GetBySku(sku);
        Console.WriteLine($"[catalog] {sku} → {product?.Name ?? "not found"} in {sw.ElapsedMilliseconds} ms");
        return product;
    }
}
""", "Catalog/ProductCatalog.cs")}
{C(r"""
using Catalog;

var db = new DbProductCatalog();
IProductCatalog catalog = new TimedProductCatalog(
                              new CachingProductCatalog(db, TimeProvider.System, TimeSpan.FromMinutes(5)));

catalog.GetBySku("SKU-TEA");     // [catalog] SKU-TEA → Assam tea 500 g in 201 ms
catalog.GetBySku("sku-tea");     // [catalog] sku-tea → Assam tea 500 g in 0 ms
catalog.GetBySku("SKU-RICE");    // [catalog] SKU-RICE → not found in 200 ms
catalog.GetBySku("SKU-RICE");    // [catalog] SKU-RICE → not found in 0 ms   (misses are cached too)
Console.WriteLine(db.Queries);   // 2
""", "Program.cs")}
<h4>Registering decorators with the container</h4>
{C(r"""
services.AddSingleton<DbProductCatalog>();
services.AddSingleton(TimeProvider.System);
services.AddSingleton<IProductCatalog>(sp =>
    new TimedProductCatalog(
        new CachingProductCatalog(sp.GetRequiredService<DbProductCatalog>(),
                                  sp.GetRequiredService<TimeProvider>(),
                                  TimeSpan.FromMinutes(5))));

// Consumers just ask for IProductCatalog and get the whole stack
""", "Program.cs (DI, fragment)")}
{warn("This hand-rolled cache uses a plain <code>Dictionary</code>, which isn't thread-safe and never evicts. In real services use <code>IMemoryCache</code> (Microsoft.Extensions.Caching.Memory) or a distributed cache inside the decorator; the pattern stays the same.", "Production note")}
{table(["","Inheritance (subclass and override)","Decorator"],[
["Adds behaviour","At compile time, to one class","At runtime, to any implementation of the interface"],
["Combining features","Class explosion: CachedLoggedDbCatalog…","Stack wrappers in any order"],
["Needs a virtual member","Yes","No — only an interface"],
["Works on sealed / third-party classes","No","Yes, if they implement (or are adapted to) the interface"]])}

<h3>2. Adapter — wrapping a third-party payment SDK</h3>
<p>The vendor SDK speaks in paise, string currency codes and numeric status codes. Your checkout wants rupees and a clear result. The adapter translates between the two, and is the only class that references the vendor's namespace.</p>
{C(r"""
// ---- Third-party SDK (you can't change it) ----
namespace PayQuick.Sdk
{
    public sealed record PqResponse(int StatusCode, string? ChargeId, string? ErrorCode);

    public sealed class PayQuickClient(string apiKey)
    {
        public PqResponse CreateCharge(long amountInPaise, string currency, string merchantRef) =>
            amountInPaise <= 0
                ? new PqResponse(400, null, "AMOUNT_INVALID")
                : new PqResponse(200, $"pq_{merchantRef}_{amountInPaise}", null);
    }
}
""", "ThirdParty/PayQuickSdk.cs (simulated)")}
{C(r"""
using PayQuick.Sdk;

namespace Checkout.Payments;

// ---- Your interface, in your terms ----
public record PaymentResult(bool Success, string? PaymentId, string? Error);

public interface IPaymentGateway
{
    PaymentResult Charge(string orderId, decimal amountInRupees);
}

// ---- The adapter ----
public sealed class PayQuickAdapter(PayQuickClient client) : IPaymentGateway
{
    public PaymentResult Charge(string orderId, decimal amountInRupees)
    {
        long paise = (long)Math.Round(amountInRupees * 100m, MidpointRounding.AwayFromZero);
        PqResponse r = client.CreateCharge(paise, "INR", orderId);

        return r.StatusCode == 200
            ? new PaymentResult(true, r.ChargeId, null)
            : new PaymentResult(false, null, Translate(r.ErrorCode));
    }

    private static string Translate(string? code) => code switch
    {
        "AMOUNT_INVALID" => "The amount must be greater than zero.",
        "CARD_DECLINED"  => "Your bank declined the payment.",
        _                => "Payment failed. Please try again."
    };
}
""", "Checkout/Payments/PayQuickAdapter.cs")}
{C(r"""
using Checkout.Payments;
using PayQuick.Sdk;      // only the composition root and the adapter see the vendor namespace

IPaymentGateway gateway = new PayQuickAdapter(new PayQuickClient("test_key"));

Console.WriteLine(gateway.Charge("ORD-77", 1_249.50m));
// PaymentResult { Success = True, PaymentId = pq_ORD-77_124950, Error =  }
Console.WriteLine(gateway.Charge("ORD-78", 0m).Error);
// The amount must be greater than zero.
""")}
<p>Switching vendors later means writing one new adapter. The same idea applies to SMS: wrap a vendor's <code>SendMessage(route, sender, mobile, text)</code> behind your <code>ISmsSender.Send(mobile, text)</code>.</p>
{table(["Pattern","Interface","Purpose"],[
["Adapter","Different from the wrapped object","Make an incompatible API fit yours"],
["Decorator","Same as the wrapped object","Add behaviour (cache, log, retry)"],
["Proxy","Same as the wrapped object","Control access (lazy load, remote, permission check)"],
["Facade","New, simpler interface over many objects","Hide a complex subsystem behind one entry point"]])}

<h3>3. Decorators in System.IO</h3>
{C(r"""
using System.IO.Compression;
using System.Security.Cryptography;

// Each Stream wraps another Stream and adds one capability
using (FileStream file = File.Create("sales-2026-11.csv.gz"))              // the real data sink
using (var buffered = new BufferedStream(file, 64 * 1024))                  // Decorator: buffering
using (var gzip = new GZipStream(buffered, CompressionLevel.Optimal))        // Decorator: compression
using (var writer = new StreamWriter(gzip))                                  // Adapter: text API over a byte Stream
{
    writer.WriteLine("City,Revenue");
    writer.WriteLine("Pune,125000");
}

// Add encryption by inserting one more wrapper — nothing else changes
using var aes = Aes.Create();
using var output = File.Create("secret.bin");
using var crypto = new CryptoStream(output, aes.CreateEncryptor(), CryptoStreamMode.Write);
crypto.Write("PAN: XXXXX1234X"u8);
""", "StreamDecorators.cs")}

<h3>4. Chain of Responsibility: middleware and HttpClient handlers</h3>
{C(r"""
// ASP.NET Core middleware (Week 17) — each component can act, short-circuit or call next
var app = WebApplication.CreateBuilder(args).Build();

app.Use(async (context, next) =>
{
    var sw = Stopwatch.StartNew();
    await next(context);                                              // pass along the chain
    Console.WriteLine($"{context.Request.Path} → {context.Response.StatusCode} in {sw.ElapsedMilliseconds} ms");
});

app.Use(async (context, next) =>
{
    if (!context.Request.Headers.ContainsKey("X-Api-Key"))
    {
        context.Response.StatusCode = 401;                            // short-circuit: later links never run
        return;
    }
    await next(context);
});

app.MapGet("/orders", () => "[]");
app.Run();
""", "Program.cs (web project, fragment)")}
{C(r"""
// HttpClient handlers: DelegatingHandler wraps an inner handler (Decorator + Chain of Responsibility)
var client = new HttpClient(new CorrelationIdHandler { InnerHandler = new HttpClientHandler() });
// In ASP.NET Core: services.AddHttpClient<PaymentsApi>().AddHttpMessageHandler<CorrelationIdHandler>();

public sealed class CorrelationIdHandler : DelegatingHandler
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        request.Headers.TryAddWithoutValidation("X-Correlation-Id", Guid.NewGuid().ToString());
        return base.SendAsync(request, ct);                           // forward to the inner handler
    }
}
""", "CorrelationIdHandler.cs")}

<h3>5. Recognising patterns in .NET</h3>
{table(["You use…","Pattern(s)","Why"],[
["<code>BufferedStream</code>, <code>GZipStream</code>, <code>CryptoStream</code>","Decorator","Same Stream interface, extra behaviour, stackable"],
["<code>StreamReader</code> / <code>StreamWriter</code>","Adapter","Text API over a byte stream"],
["ASP.NET Core middleware","Chain of Responsibility","Each component handles, short-circuits or passes on"],
["<code>DelegatingHandler</code> in HttpClient","Chain of Responsibility / Decorator","Retries, auth headers, logging around the real handler"],
["<code>IEnumerable&lt;T&gt;</code> / <code>IEnumerator&lt;T&gt;</code>, <code>yield</code>","Iterator","Walk any collection without knowing its structure (Week 4)"],
["<code>ILogger&lt;T&gt;</code> + logging providers","Abstraction (DIP) + Strategy/Composite","Code logs to one interface; providers (console, file, Application Insights) are plug-ins, and one log call fans out to all"],
["<code>ILoggerFactory</code>, <code>IHttpClientFactory</code>","Factory","Create configured instances"],
["<code>StringBuilder</code>, <code>WebApplication.CreateBuilder</code>","Builder","Step-by-step construction, then Build/ToString"],
["C# events, <code>IObservable&lt;T&gt;</code>","Observer","Publish/subscribe"],
["<code>IComparer&lt;T&gt;</code> passed to Sort","Strategy","Pluggable comparison algorithm (Week 4)"],
["<code>Lazy&lt;T&gt;</code>, EF Core lazy-loading proxies","Proxy / lazy initialisation","Defer expensive work until first use"],
["<code>HttpClient</code> itself","Facade","Simple API over connection pooling, DNS, TLS, HTTP/2"]])}
{tip("In interviews, \"name a pattern you've used\" is best answered with a .NET example plus why: \"Middleware is a chain of responsibility; I wrote one that adds a correlation id and short-circuits unauthenticated requests.\"")}
''',
["Decorators that don't implement the full interface, so some calls bypass the added behaviour.",
"Putting business logic in a decorator; keep decorators for cross-cutting concerns.",
"Letting vendor types (<code>PqResponse</code>) leak through the adapter into controllers and domain code.",
"Converting rupees to paise from a <code>double</code>: <code>(long)(19.99 * 100)</code> is 1998, not 1999. Keep money in <code>decimal</code> and round before casting.",
"Forgetting to call <code>next</code> in middleware, accidentally short-circuiting every request."],
("40 min", ["Write a <code>RetryingProductCatalog</code> decorator that retries up to 3 times on <code>TimeoutException</code>, and stack it under the cache.",
"Create an <code>ISmsSender</code> interface and an adapter for a fake vendor class <code>BulkSmsClient.Push(string route, string senderId, string msisdn, string text)</code> that returns \"OK:id\" or \"ERR:code\".",
"Wrap a <code>FileStream</code> in a custom <code>CountingStream : Stream</code> decorator that counts bytes written, and put it between a <code>GZipStream</code> and the file to measure compressed size."]),
[("What makes a class a Decorator rather than just a wrapper?","It implements the same interface as the object it wraps and forwards to it, so it can be substituted transparently and stacked with other decorators."),
("Why should a third-party SDK sit behind an adapter?","So your code depends on your own interface: the vendor can be replaced or faked in tests, and its types, units and error codes don't spread through your domain."),
("Which pattern does ASP.NET Core middleware implement?","Chain of Responsibility: each middleware receives the request and a <code>next</code> delegate, and decides whether to handle it, modify it, or pass it on.")],
[("Basic","What is the Decorator pattern? Give a .NET example.","A wrapper that implements the same interface as the object it wraps, adding behaviour before or after delegating. Examples: GZipStream wrapping a FileStream, a caching repository wrapping a database repository, DelegatingHandler in HttpClient."),
("Basic","What is the Adapter pattern?","It converts one interface into another that clients expect, e.g. wrapping a vendor payment SDK that works in paise and status codes behind your IPaymentGateway that works in rupees and PaymentResult."),
("Basic","Name three design patterns used inside .NET itself.","Iterator (IEnumerable/yield), Decorator (Stream wrappers), Chain of Responsibility (ASP.NET Core middleware), Builder (StringBuilder, WebApplicationBuilder), Observer (events), Factory (IHttpClientFactory)."),
("Intermediate","How would you add caching to a repository without changing it?","Write a CachingRepository that implements the same interface, takes the real repository in its constructor, checks a cache first and delegates on a miss. Register it in DI so consumers receive the decorated instance (factory lambda or Scrutor's Decorate)."),
("Intermediate","Decorator vs Proxy vs Adapter?","All wrap another object. Adapter changes the interface to fit a client. Decorator keeps the interface and adds behaviour. Proxy keeps the interface and controls access (lazy creation, remote calls, permission checks)."),
("Intermediate","How is a DelegatingHandler both a Decorator and a link in a chain?","It wraps an InnerHandler with the same SendAsync signature (decorator), and handlers are linked so each passes the request to the next until the primary HttpClientHandler sends it (chain of responsibility). Each can modify the request, short-circuit, or inspect the response.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 7: Parking lot system — design first, then code",
"Practise the classic low-level-design interview: turn requirements into a class diagram, then into a working Core library and console app with levels, sized slots, vehicles, tickets and live availability. Budget: about 4 hours.",
[("Low-level design (LLD)","Designing classes, their responsibilities and relationships for one component; a standard interview round."),
("Noun/verb analysis","Underline nouns in the requirements (candidate classes) and verbs (candidate methods)."),
("Composition","A whole that owns its parts' lifetime: a lot owns its levels, a level owns its slots."),
("Slot allocation","The rule that picks which free slot a vehicle gets."),
("Smallest fit","Give a vehicle the smallest free slot it fits, so big slots stay free for big vehicles."),
("Ticket","The record of one stay: vehicle, slot, entry time, exit time and amount.")],
["Design on paper first: requirements → nouns and verbs → class diagram → code.",
"Core holds every rule; the console app only reads input and prints results.",
"Today's pricing is a deliberate <code>switch</code>; tomorrow you refactor it to Strategy (OCP in action).",
"Slots are built by hand in Program.cs today; tomorrow a Factory builds them from configuration.",
"Inject <code>IClock</code> (from Week 2) so you can fast-forward time to test fees."],
f'''
<h3>1. Requirements</h3>
<ul>
<li>The lot has one or more <b>levels</b>; each level has numbered <b>slots</b> of three sizes: <b>Small</b>, <b>Medium</b>, <b>Large</b>.</li>
<li>Vehicles are <b>Bike</b>, <b>Car</b> or <b>Truck</b>, identified by an Indian registration number (e.g. <code>KA01AB1234</code>), normalised to upper case without spaces or dashes.</li>
<li>A bike needs Small, a car Medium, a truck Large. A vehicle may use a <i>larger</i> slot if its own size is full (bike in a car slot), never a smaller one.</li>
<li><b>Allocation:</b> smallest fitting size first, then lowest level, then lowest slot number.</li>
<li>Parking issues a <b>ticket</b> (<code>T0001</code>, <code>T0002</code>…) with entry time; the same vehicle can't be parked twice.</li>
<li>Exiting with a ticket id frees the slot, records the exit time and charges a fee: ₹10/h bike, ₹40/h car, ₹100/h truck, any part hour counts as an hour, minimum one hour.</li>
<li><b>Availability display:</b> free/total per size per level, plus how many more bikes, cars and trucks fit.</li>
<li>Console menu: availability, park, exit, open tickets, find a vehicle, advance the clock (for testing).</li>
</ul>

<h3>2. From nouns and verbs to classes</h3>
{table(["Noun / verb in the requirements","Becomes"],[
["lot, level, slot, vehicle, ticket","Classes: <code>ParkingLotService</code>, <code>Level</code>, <code>ParkingSlot</code>, <code>Vehicle</code>, <code>Ticket</code>"],
["Small / Medium / Large, Bike / Car / Truck","Enums: <code>SlotSize</code>, <code>VehicleType</code>"],
["park, exit","<code>ParkingLotService.Park(Vehicle)</code>, <code>Exit(ticketId)</code> returning <code>Result&lt;Ticket&gt;</code>"],
["fits","<code>ParkingSlot.CanFit(VehicleType)</code> — the slot knows its own rule (information expert)"],
["free / total per level","<code>Availability()</code> returning small records"],
["time, fee","<code>IClock</code> (injected), fee calculation (a switch today, a strategy tomorrow)"]])}

<h3>3. Class diagram</h3>
<pre class="mermaid">
classDiagram
  direction LR
  class ParkingLotService
  ParkingLotService : +string Name
  ParkingLotService : +Park(Vehicle) Result~Ticket~
  ParkingLotService : +Exit(string ticketId) Result~Ticket~
  ParkingLotService : +Availability() List~LevelAvailability~
  ParkingLotService : +FreeSlotsFor(VehicleType) int
  class Level
  Level : +int Number
  Level : +List~ParkingSlot~ Slots
  class ParkingSlot
  ParkingSlot : +string Id
  ParkingSlot : +SlotSize Size
  ParkingSlot : +Vehicle Occupant
  ParkingSlot : +CanFit(VehicleType) bool
  class Vehicle
  Vehicle : +string Number
  Vehicle : +VehicleType Type
  class Ticket
  Ticket : +string Id
  Ticket : +DateTime EntryTime
  Ticket : +DateTime ExitTime
  Ticket : +decimal Amount
  class IClock
  &lt;&lt;interface&gt;&gt; IClock
  IClock : +DateTime Now
  ParkingLotService "1" *-- "1..*" Level : levels
  Level "1" *-- "1..*" ParkingSlot : slots
  ParkingSlot --&gt; "0..1" Vehicle : occupant
  ParkingLotService --&gt; "*" Ticket : issues
  Ticket --&gt; Vehicle
  ParkingLotService ..&gt; IClock : uses
</pre>
<p class="muted">Filled diamonds (<code>*--</code>) are composition: levels and slots don't exist without their lot. Draw this on paper before reading the code below — in an interview the diagram is half the marks.</p>

<h3>4. Scaffold</h3>
{C(r"""
dotnet new sln -n ParkingLot
dotnet new classlib -n ParkingLot.Core
dotnet new console  -n ParkingLot.App
dotnet sln add ParkingLot.Core ParkingLot.App
dotnet add ParkingLot.App reference ParkingLot.Core
rm ParkingLot.Core/Class1.cs
""", lang="bash")}
{C(r"""
ParkingLot/
├─ ParkingLot.sln
├─ ParkingLot.Core/
│  ├─ Result.cs
│  ├─ Clock.cs
│  ├─ Models/
│  │  ├─ Enums.cs
│  │  ├─ Vehicle.cs
│  │  ├─ ParkingSlot.cs
│  │  ├─ Level.cs
│  │  ├─ Ticket.cs
│  │  └─ Availability.cs
│  └─ Services/
│     └─ ParkingLotService.cs
└─ ParkingLot.App/
   ├─ ConsoleInput.cs
   └─ Program.cs
""", lang="text")}

<h3>Step 1 — Result and clock</h3>
{C(r"""
namespace ParkingLot.Core;

public readonly record struct Result<T>(bool Success, T? Value, string? Error)
{
    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);
}
""", "ParkingLot.Core/Result.cs")}
{C(r"""
namespace ParkingLot.Core;

public interface IClock
{
    DateTime Now { get; }
}

public sealed class SystemClock : IClock
{
    public DateTime Now => DateTime.Now;
}

// For the console demo and for tests: time only moves when you say so
public sealed class ManualClock(DateTime start) : IClock
{
    public DateTime Now { get; private set; } = start;

    public void Advance(TimeSpan by)
    {
        if (by < TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(by), "Time can't go backwards");
        Now += by;
    }
}
""", "ParkingLot.Core/Clock.cs")}

<h3>Step 2 — Enums and Vehicle</h3>
{C(r"""
namespace ParkingLot.Core.Models;

public enum VehicleType { Bike, Car, Truck }

// Explicit values so sizes can be compared: Small < Medium < Large
public enum SlotSize { Small = 1, Medium = 2, Large = 3 }
""", "ParkingLot.Core/Models/Enums.cs")}
{C(r"""
using System.Text.RegularExpressions;

namespace ParkingLot.Core.Models;

public sealed record Vehicle
{
    // Simplified Indian format: state code, RTO number, 0–3 series letters, 4 digits (KA01AB1234, DL3CAF0001)
    private static readonly Regex Format = new(@"^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{4}$", RegexOptions.Compiled);

    public string Number { get; }
    public VehicleType Type { get; }

    public Vehicle(string number, VehicleType type)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(number);
        if (!Enum.IsDefined(type)) throw new ArgumentOutOfRangeException(nameof(type));

        string normalised = Normalise(number);
        if (!Format.IsMatch(normalised))
            throw new ArgumentException($"'{number}' is not a valid registration number", nameof(number));

        Number = normalised;
        Type = type;
    }

    public static string Normalise(string number) =>
        number.Replace(" ", "").Replace("-", "").ToUpperInvariant();

    public override string ToString() => $"{Type} {Number}";
}
""", "ParkingLot.Core/Models/Vehicle.cs")}

<h3>Step 3 — ParkingSlot and Level</h3>
{C(r"""
namespace ParkingLot.Core.Models;

public class ParkingSlot
{
    public string Id { get; }
    public int Level { get; }
    public SlotSize Size { get; }
    public Vehicle? Occupant { get; private set; }
    public bool IsFree => Occupant is null;

    public ParkingSlot(string id, int level, SlotSize size)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(id);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(level);
        if (!Enum.IsDefined(size)) throw new ArgumentOutOfRangeException(nameof(size));
        (Id, Level, Size) = (id, level, size);
    }

    public static SlotSize RequiredSize(VehicleType type) => type switch
    {
        VehicleType.Bike  => SlotSize.Small,
        VehicleType.Car   => SlotSize.Medium,
        VehicleType.Truck => SlotSize.Large,
        _ => throw new ArgumentOutOfRangeException(nameof(type))
    };

    // A vehicle fits its own size or anything larger
    public bool CanFit(VehicleType type) => Size >= RequiredSize(type);

    public virtual string Describe() => Id;          // subclasses (EV slots, tomorrow) add detail

    internal void Assign(Vehicle vehicle)
    {
        if (!IsFree) throw new InvalidOperationException($"Slot {Id} is occupied by {Occupant}");
        if (!CanFit(vehicle.Type)) throw new InvalidOperationException($"A {vehicle.Type} doesn't fit slot {Id}");
        Occupant = vehicle;
    }

    internal void Release()
    {
        if (IsFree) throw new InvalidOperationException($"Slot {Id} is already free");
        Occupant = null;
    }
}
""", "ParkingLot.Core/Models/ParkingSlot.cs")}
{C(r"""
namespace ParkingLot.Core.Models;

public class Level
{
    public int Number { get; }
    public IReadOnlyList<ParkingSlot> Slots { get; }

    public Level(int number, IEnumerable<ParkingSlot> slots)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(number);
        var list = slots.ToList();
        if (list.Count == 0)
            throw new ArgumentException($"Level {number} has no slots", nameof(slots));
        if (list.Any(s => s.Level != number))
            throw new ArgumentException($"Every slot on level {number} must belong to level {number}", nameof(slots));

        Number = number;
        Slots = list.AsReadOnly();
    }
}
""", "ParkingLot.Core/Models/Level.cs")}

<h3>Step 4 — Ticket and availability records</h3>
{C(r"""
namespace ParkingLot.Core.Models;

public class Ticket
{
    public string Id { get; }
    public Vehicle Vehicle { get; }
    public string SlotId { get; }
    public int Level { get; }
    public DateTime EntryTime { get; }
    public DateTime? ExitTime { get; private set; }
    public decimal? Amount { get; private set; }
    public bool IsOpen => ExitTime is null;

    internal Ticket(string id, Vehicle vehicle, ParkingSlot slot, DateTime entryTime)
    {
        Id = id;
        Vehicle = vehicle;
        SlotId = slot.Id;
        Level = slot.Level;
        EntryTime = entryTime;
    }

    public TimeSpan Duration(DateTime now) => (ExitTime ?? now) - EntryTime;

    internal void Close(DateTime exitTime, decimal amount)
    {
        if (!IsOpen) throw new InvalidOperationException($"Ticket {Id} is already closed");
        if (exitTime < EntryTime) throw new ArgumentException("Exit can't be before entry", nameof(exitTime));
        ArgumentOutOfRangeException.ThrowIfNegative(amount);
        ExitTime = exitTime;
        Amount = amount;
    }

    public override string ToString() =>
        $"{Id}  {Vehicle,-16} {SlotId,-7} in {EntryTime:ddd HH:mm}" +
        (ExitTime is { } exit ? $"  out {exit:ddd HH:mm}  ₹{Amount:N2}" : "");
}
""", "ParkingLot.Core/Models/Ticket.cs")}
{C(r"""
namespace ParkingLot.Core.Models;

public sealed record SlotCount(SlotSize Size, int Free, int Total);

public sealed record LevelAvailability(int Level, IReadOnlyList<SlotCount> Counts);
""", "ParkingLot.Core/Models/Availability.cs")}

<h3>Step 5 — ParkingLotService</h3>
{C(r"""
using ParkingLot.Core.Models;

namespace ParkingLot.Core.Services;

public class ParkingLotService
{
    private readonly IReadOnlyList<Level> _levels;
    private readonly IClock _clock;
    private readonly Dictionary<string, ParkingSlot> _slotsById;
    private readonly Dictionary<string, Ticket> _openById = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, Ticket> _openByVehicle = new(StringComparer.OrdinalIgnoreCase);
    private readonly List<Ticket> _closed = [];
    private int _ticketSequence;

    public string Name { get; }
    public IReadOnlyList<Level> Levels => _levels;
    public IReadOnlyCollection<Ticket> OpenTickets => _openById.Values;
    public IReadOnlyList<Ticket> ClosedTickets => _closed;

    public ParkingLotService(string name, IEnumerable<Level> levels, IClock clock)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        Name = name;
        _clock = clock ?? throw new ArgumentNullException(nameof(clock));
        _levels = levels.OrderBy(l => l.Number).ToList();
        if (_levels.Count == 0) throw new ArgumentException("A lot needs at least one level", nameof(levels));
        if (_levels.Select(l => l.Number).Distinct().Count() != _levels.Count)
            throw new ArgumentException("Level numbers must be unique", nameof(levels));

        // Throws ArgumentException on duplicate slot ids — a configuration bug we want to catch at startup
        _slotsById = _levels.SelectMany(l => l.Slots).ToDictionary(s => s.Id, StringComparer.OrdinalIgnoreCase);
    }

    public Result<Ticket> Park(Vehicle vehicle)
    {
        ArgumentNullException.ThrowIfNull(vehicle);
        if (_openByVehicle.TryGetValue(vehicle.Number, out var existing))
            return Result<Ticket>.Fail($"{vehicle.Number} is already parked at {existing.SlotId} (ticket {existing.Id})");

        ParkingSlot? slot = FindSlot(vehicle.Type);
        if (slot is null)
            return Result<Ticket>.Fail($"No free slot for a {vehicle.Type}");

        slot.Assign(vehicle);
        var ticket = new Ticket($"T{++_ticketSequence:D4}", vehicle, slot, _clock.Now);
        _openById.Add(ticket.Id, ticket);
        _openByVehicle.Add(vehicle.Number, ticket);
        return Result<Ticket>.Ok(ticket);
    }

    public Result<Ticket> Exit(string ticketId)
    {
        if (string.IsNullOrWhiteSpace(ticketId) || !_openById.Remove(ticketId.Trim(), out var ticket))
            return Result<Ticket>.Fail($"No open ticket '{ticketId}'");

        DateTime now = _clock.Now;
        ticket.Close(now, CalculateFee(ticket.Vehicle.Type, ticket.EntryTime, now));
        _openByVehicle.Remove(ticket.Vehicle.Number);
        _slotsById[ticket.SlotId].Release();
        _closed.Add(ticket);
        return Result<Ticket>.Ok(ticket);
    }

    public Ticket? FindByVehicle(string number) =>
        _openByVehicle.GetValueOrDefault(Vehicle.Normalise(number));

    public int FreeSlotsFor(VehicleType type) =>
        _slotsById.Values.Count(s => s.IsFree && s.CanFit(type));

    public IReadOnlyList<LevelAvailability> Availability() =>
        _levels.Select(level => new LevelAvailability(level.Number,
                    Enum.GetValues<SlotSize>()
                        .Select(size => new SlotCount(size,
                            Free:  level.Slots.Count(s => s.Size == size && s.IsFree),
                            Total: level.Slots.Count(s => s.Size == size)))
                        .ToList()))
               .ToList();

    // Smallest fitting size first, then lowest level, then slot order (OrderBy is stable)
    private ParkingSlot? FindSlot(VehicleType type) =>
        _levels.SelectMany(l => l.Slots)
               .Where(s => s.IsFree && s.CanFit(type))
               .OrderBy(s => s.Size)
               .ThenBy(s => s.Level)
               .FirstOrDefault();

    // ⚠ Saturday version: a switch we'll have to edit for every pricing change. Sunday → Strategy.
    private static decimal CalculateFee(VehicleType type, DateTime entry, DateTime exit)
    {
        decimal ratePerHour = type switch
        {
            VehicleType.Bike  => 10m,
            VehicleType.Car   => 40m,
            VehicleType.Truck => 100m,
            _ => throw new ArgumentOutOfRangeException(nameof(type))
        };
        int hours = Math.Max(1, (int)Math.Ceiling((exit - entry).TotalHours));
        return hours * ratePerHour;
    }
}
""", "ParkingLot.Core/Services/ParkingLotService.cs")}
{tip("<code>Result&lt;Ticket&gt;</code> is for expected outcomes (lot full, already parked, unknown ticket). Exceptions remain for bugs and invalid input, such as an invalid registration number or assigning an occupied slot.")}

<h3>Step 6 — Console input helper</h3>
{C(r"""
namespace ParkingLot.App;

public static class ConsoleInput
{
    public static string ReadText(string prompt)
    {
        while (true)
        {
            Console.Write(prompt);
            string line = Console.ReadLine() ?? throw new InvalidOperationException("Input closed");
            if (!string.IsNullOrWhiteSpace(line)) return line.Trim();
            Console.WriteLine("  Please enter a value.");
        }
    }

    public static int ReadChoice(string prompt, int min, int max)
    {
        while (true)
        {
            Console.Write(prompt);
            string line = Console.ReadLine() ?? throw new InvalidOperationException("Input closed");
            if (int.TryParse(line, out int n) && n >= min && n <= max) return n;
            Console.WriteLine($"  Enter a number from {min} to {max}.");
        }
    }
}
""", "ParkingLot.App/ConsoleInput.cs")}

<h3>Step 7 — Program.cs</h3>
{C(r"""
using ParkingLot.App;
using ParkingLot.Core;
using ParkingLot.Core.Models;
using ParkingLot.Core.Services;

var clock = new ManualClock(new DateTime(2026, 11, 13, 9, 0, 0));      // Fri 13 Nov 2026, 09:00
var lot = new ParkingLotService("City Centre Parking, Pune", BuildLevels(levelCount: 2), clock);

int choice;
do
{
    Console.WriteLine($"\n==== {lot.Name} · {clock.Now:ddd dd MMM HH:mm} ====");
    Console.WriteLine("1) Availability  2) Park  3) Exit  4) Open tickets  5) Find vehicle  6) Advance clock  0) Quit");
    choice = ConsoleInput.ReadChoice("Choose: ", 0, 6);
    try
    {
        switch (choice)
        {
            case 1: ShowAvailability(); break;
            case 2: Park(); break;
            case 3: Leave(); break;
            case 4:
                foreach (var t in lot.OpenTickets) Console.WriteLine($"  {t}");
                if (lot.OpenTickets.Count == 0) Console.WriteLine("  (no vehicles parked)");
                break;
            case 5:
                var found = lot.FindByVehicle(ConsoleInput.ReadText("Registration: "));
                Console.WriteLine(found is null ? "  Not in the lot" : $"  {found}");
                break;
            case 6:
                clock.Advance(TimeSpan.FromMinutes(ConsoleInput.ReadChoice("Minutes: ", 1, 7 * 24 * 60)));
                break;
        }
    }
    catch (ArgumentException ex)                       // invalid registration number etc.
    {
        Console.WriteLine($"  ✗ {ex.Message}");
    }
} while (choice != 0);

void Park()
{
    var type = (VehicleType)(ConsoleInput.ReadChoice("1) Bike  2) Car  3) Truck: ", 1, 3) - 1);
    var vehicle = new Vehicle(ConsoleInput.ReadText("Registration: "), type);
    var r = lot.Park(vehicle);
    Console.WriteLine(r.Success
        ? $"  ✓ Ticket {r.Value!.Id}: {vehicle} → {r.Value.SlotId} (level {r.Value.Level}) at {r.Value.EntryTime:HH:mm}"
        : $"  ✗ {r.Error}");
}

void Leave()
{
    var r = lot.Exit(ConsoleInput.ReadText("Ticket id: "));
    if (!r.Success) { Console.WriteLine($"  ✗ {r.Error}"); return; }
    var t = r.Value!;
    Console.WriteLine($"  ✓ {t.Vehicle} left at {t.ExitTime:HH:mm} after {Format(t.Duration(clock.Now))} → ₹{t.Amount:N2}");
}

void ShowAvailability()
{
    Console.WriteLine($"  {"Level",-7}{"Small",-9}{"Medium",-9}{"Large",-9}");
    foreach (var level in lot.Availability())
    {
        Console.Write($"  L{level.Level,-6}");
        foreach (var c in level.Counts) Console.Write($"{c.Free + "/" + c.Total,-9}");
        Console.WriteLine();
    }
    Console.WriteLine("  Free for → " + string.Join("  ",
        Enum.GetValues<VehicleType>().Select(t => $"{t}: {lot.FreeSlotsFor(t)}")));
}

static string Format(TimeSpan d) => $"{(int)d.TotalHours}h {d.Minutes:D2}m";

// Today: built by hand. Tomorrow: a factory builds this from configuration.
static List<Level> BuildLevels(int levelCount)
{
    var levels = new List<Level>();
    for (int lvl = 1; lvl <= levelCount; lvl++)
    {
        var slots = new List<ParkingSlot>();
        int n = 1;
        for (int i = 0; i < 2; i++) slots.Add(new ParkingSlot($"L{lvl}-S{n++:D2}", lvl, SlotSize.Small));
        for (int i = 0; i < 3; i++) slots.Add(new ParkingSlot($"L{lvl}-M{n++:D2}", lvl, SlotSize.Medium));
        slots.Add(new ParkingSlot($"L{lvl}-L{n++:D2}", lvl, SlotSize.Large));
        levels.Add(new Level(lvl, slots));
    }
    return levels;
}
""", "ParkingLot.App/Program.cs")}

<h3>Run it</h3>
{C(r"""
dotnet run --project ParkingLot.App
""", lang="bash")}
{C(r"""
==== City Centre Parking, Pune · Fri 13 Nov 09:00 ====
Choose: 2
1) Bike  2) Car  3) Truck: 2
Registration: ka 01 ab 1234
  ✓ Ticket T0001: Car KA01AB1234 → L1-M03 (level 1) at 09:00
Choose: 2
1) Bike  2) Car  3) Truck: 3
Registration: MH12TR0001
  ✓ Ticket T0002: Truck MH12TR0001 → L1-L06 (level 1) at 09:00
Choose: 1
  Level  Small    Medium   Large
  L1     2/2      2/3      0/1
  L2     2/2      3/3      1/1
  Free for → Bike: 10  Car: 6  Truck: 1
Choose: 6
Minutes: 150
Choose: 3
Ticket id: t0001
  ✓ Car KA01AB1234 left at 11:30 after 2h 30m → ₹120.00
Choose: 2
1) Bike  2) Car  3) Truck: 2
Registration: HELLO
  ✗ 'HELLO' is not a valid registration number (Parameter 'number')
""", lang="text")}
<p class="muted">The menu header is printed before every \"Choose:\"; it's omitted above for brevity. <code>ArgumentException.Message</code> appends the parameter name — strip it with a custom exception (Week 3) if you want a cleaner message.</p>

<h3>Stretch goals</h3>
<ul>
<li>Add a <code>Lost ticket</code> option: find the open ticket by registration number and charge a ₹200 penalty on top.</li>
<li>Make overflow configurable: a flag that stops bikes from taking car slots.</li>
<li>Print a level map: <code>[S·][S·][M■][M·][M·][L■]</code> where ■ is occupied.</li>
<li>Show today's revenue and the busiest hour from <code>ClosedTickets</code> using LINQ (Week 5).</li>
</ul>
''',
iqs=[("Basic","How do you approach a low-level design question like \"design a parking lot\"?","Clarify requirements and scope (vehicle types, slot sizes, pricing, multiple levels, payment?), list nouns and verbs, draw a class diagram with responsibilities and relationships, call out extension points (pricing, allocation), then code the core flows: park, exit, availability."),
("Basic","Why does ParkingSlot own CanFit instead of the service?","Information expert: the slot has the data (its size) needed to decide, so the rule lives with the data. The service only orchestrates; changing the fit rule touches one class."),
("Intermediate","Why keep two dictionaries of open tickets (by id and by vehicle)?","They give O(1) lookup for both access paths: exiting by ticket id and checking or finding a vehicle by registration number. The cost is keeping them consistent, so they're only modified together inside Park and Exit."),
("Intermediate","How would you make Park safe if two entry gates call it at the same time?","Today's in-memory service isn't thread-safe: two gates could get the same free slot. Wrap the find-and-assign step in a lock (or use one lock per lot), or in a database use a transaction with a conditional update (UPDATE slot SET occupied = 1 WHERE id = @id AND occupied = 0) and retry if no row changed.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Parking lot: Strategy pricing, slot Factory, Observer alerts — then README and revision",
"Refactor yesterday's parking lot with the week's patterns: pluggable pricing strategies, slots created by a factory from configuration, and observers for \"lot full\" alerts. Then test it, document it and revise.",
[("Pricing strategy","An interchangeable fee algorithm: hourly, flat-rate per day, or a peak/weekend surcharge."),
("Grace period","A short free window (e.g. 10 minutes) for drivers who enter and leave immediately."),
("Peak pricing","A multiplier applied when entry falls in busy hours or on weekends."),
("Layout configuration","Data describing how many slots of each size each level has, instead of hard-coded loops."),
("Capacity event","A notification raised when free slots for a vehicle type drop to zero or become available again.")],
["Pricing moves out of the service into <code>IPricingStrategy</code> implementations; the service never changes for new tariffs.",
"<code>PeakPricing</code> wraps another strategy — Strategy and Decorator together.",
"<code>ISlotFactory</code> + <code>LotFactory</code> build levels from <code>LevelConfig</code> records; an <code>EvSlotFactory</code> adds EV slots without touching the others.",
"<code>ParkingLotService</code> raises <code>LotFull</code> and <code>SpaceAvailable</code>; the display board and manager alert subscribe.",
"Program.cs becomes a composition root that picks concrete strategies, factories and observers."],
f'''
<h3>1. Pricing via Strategy</h3>
{C(r"""
using ParkingLot.Core.Models;

namespace ParkingLot.Core.Pricing;

public interface IPricingStrategy
{
    string Name { get; }
    decimal Calculate(VehicleType type, DateTime entry, DateTime exit);
}

internal static class Stay
{
    public static TimeSpan Length(DateTime entry, DateTime exit) =>
        exit >= entry ? exit - entry : throw new ArgumentException("Exit can't be before entry", nameof(exit));

    public static void RequireAllTypes(IReadOnlyDictionary<VehicleType, decimal> rates, string paramName)
    {
        foreach (var type in Enum.GetValues<VehicleType>())
        {
            if (!rates.TryGetValue(type, out var rate))
                throw new ArgumentException($"No rate for {type}", paramName);
            if (rate < 0) throw new ArgumentOutOfRangeException(paramName, $"Rate for {type} is negative");
        }
    }
}

// Per vehicle type, per started hour, with a free grace period
public sealed class HourlyPricing : IPricingStrategy
{
    private readonly IReadOnlyDictionary<VehicleType, decimal> _ratePerHour;
    private readonly TimeSpan _grace;

    public HourlyPricing(IReadOnlyDictionary<VehicleType, decimal> ratePerHour, TimeSpan? grace = null)
    {
        Stay.RequireAllTypes(ratePerHour, nameof(ratePerHour));
        _ratePerHour = ratePerHour;
        _grace = grace ?? TimeSpan.FromMinutes(10);
    }

    public string Name => "Hourly";

    public decimal Calculate(VehicleType type, DateTime entry, DateTime exit)
    {
        TimeSpan length = Stay.Length(entry, exit);
        if (length <= _grace) return 0m;
        int hours = (int)Math.Ceiling(length.TotalHours);
        return hours * _ratePerHour[type];
    }
}

// One price per started 24 hours, per vehicle type
public sealed class FlatRatePricing : IPricingStrategy
{
    private readonly IReadOnlyDictionary<VehicleType, decimal> _ratePerDay;

    public FlatRatePricing(IReadOnlyDictionary<VehicleType, decimal> ratePerDay)
    {
        Stay.RequireAllTypes(ratePerDay, nameof(ratePerDay));
        _ratePerDay = ratePerDay;
    }

    public string Name => "Flat per day";

    public decimal Calculate(VehicleType type, DateTime entry, DateTime exit)
    {
        int days = Math.Max(1, (int)Math.Ceiling(Stay.Length(entry, exit).TotalDays));
        return days * _ratePerDay[type];
    }
}

// Wraps ANY strategy: weekends and weekday evenings (17:00–21:00) cost more, judged by entry time
public sealed class PeakPricing(IPricingStrategy inner, decimal multiplier = 1.5m) : IPricingStrategy
{
    private readonly decimal _multiplier = multiplier >= 1m
        ? multiplier
        : throw new ArgumentOutOfRangeException(nameof(multiplier), "Peak multiplier must be at least 1");

    public string Name => $"{inner.Name} + peak ×{_multiplier}";

    public static bool IsPeak(DateTime t) =>
        t.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday || (t.Hour >= 17 && t.Hour < 21);

    public decimal Calculate(VehicleType type, DateTime entry, DateTime exit)
    {
        decimal basePrice = inner.Calculate(type, entry, exit);
        return IsPeak(entry) ? Math.Round(basePrice * _multiplier, 0, MidpointRounding.AwayFromZero) : basePrice;
    }
}
""", "ParkingLot.Core/Pricing/PricingStrategies.cs")}
{table(["Car stay","Hourly","Peak(Hourly)","Flat per day"],[
["Fri 09:00 → 09:08","₹0 (grace)","₹0","₹200"],
["Fri 09:00 → 09:11","₹40","₹40","₹200"],
["Fri 09:00 → 11:30","₹120","₹120","₹200"],
["Fri 18:00 → 20:00","₹80","₹120 (evening peak)","₹200"],
["Sat 10:00 → 13:00","₹120","₹180 (weekend)","₹200"],
["Fri 09:00 → Sat 11:00 (26 h)","₹1,040","₹1,040 (entry not peak)","₹400"]])}

<h3>2. Slots via Factory</h3>
{C(r"""
namespace ParkingLot.Core.Models;

// An EV bay is a Medium slot with a charger; only the description differs for now
public sealed class EvChargingSlot(string id, int level) : ParkingSlot(id, level, SlotSize.Medium)
{
    public override string Describe() => $"{Id} (EV charger)";
}
""", "ParkingLot.Core/Models/EvChargingSlot.cs")}
{C(r"""
using ParkingLot.Core.Models;

namespace ParkingLot.Core.Setup;

public sealed record LevelConfig(int Level, int Small, int Medium, int Large);

public interface ISlotFactory
{
    ParkingSlot Create(int level, SlotSize size, int position);
}

// The one place that knows the id format: L1-S01, L1-M03, L2-L06
public sealed class StandardSlotFactory : ISlotFactory
{
    public static string IdFor(int level, SlotSize size, int position)
    {
        char code = size switch
        {
            SlotSize.Small => 'S',
            SlotSize.Medium => 'M',
            SlotSize.Large => 'L',
            _ => throw new ArgumentOutOfRangeException(nameof(size))
        };
        return $"L{level}-{code}{position:D2}";
    }

    public ParkingSlot Create(int level, SlotSize size, int position) =>
        new(IdFor(level, size, position), level, size);
}

// Makes every Medium slot on one level an EV bay; delegates everything else
public sealed class EvSlotFactory(ISlotFactory inner, int evLevel) : ISlotFactory
{
    public ParkingSlot Create(int level, SlotSize size, int position) =>
        level == evLevel && size == SlotSize.Medium
            ? new EvChargingSlot(StandardSlotFactory.IdFor(level, size, position), level)
            : inner.Create(level, size, position);
}

public static class LotFactory
{
    public static IReadOnlyList<Level> CreateLevels(IEnumerable<LevelConfig> layout, ISlotFactory slotFactory)
    {
        var levels = new List<Level>();
        var seen = new HashSet<int>();

        foreach (var cfg in layout)
        {
            if (!seen.Add(cfg.Level))
                throw new ArgumentException($"Level {cfg.Level} is configured twice", nameof(layout));
            if (cfg.Small < 0 || cfg.Medium < 0 || cfg.Large < 0)
                throw new ArgumentException($"Level {cfg.Level} has a negative slot count", nameof(layout));

            var slots = new List<ParkingSlot>();
            int position = 1;
            foreach (var (size, count) in new[] { (SlotSize.Small, cfg.Small), (SlotSize.Medium, cfg.Medium), (SlotSize.Large, cfg.Large) })
                for (int i = 0; i < count; i++)
                    slots.Add(slotFactory.Create(cfg.Level, size, position++));

            levels.Add(new Level(cfg.Level, slots));       // Level rejects a level with zero slots
        }
        return levels;
    }
}
""", "ParkingLot.Core/Setup/SlotFactories.cs")}
{tip("The layout could now come from <code>appsettings.json</code> (Week 18 configuration) instead of code: the factory doesn't care where <code>LevelConfig</code> records come from.")}

<h3>3. Observer for \"lot full\" alerts — the updated service</h3>
{C(r"""
using ParkingLot.Core.Models;
using ParkingLot.Core.Pricing;

namespace ParkingLot.Core.Services;

public sealed class CapacityEventArgs(VehicleType vehicleType, int freeSlots, DateTime at) : EventArgs
{
    public VehicleType VehicleType { get; } = vehicleType;
    public int FreeSlots { get; } = freeSlots;
    public DateTime At { get; } = at;
}

public class ParkingLotService
{
    private readonly IReadOnlyList<Level> _levels;
    private readonly IClock _clock;
    private readonly Dictionary<string, ParkingSlot> _slotsById;
    private readonly Dictionary<string, Ticket> _openById = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, Ticket> _openByVehicle = new(StringComparer.OrdinalIgnoreCase);
    private readonly List<Ticket> _closed = [];
    private IPricingStrategy _pricing;
    private int _ticketSequence;

    public event EventHandler<CapacityEventArgs>? LotFull;          // no slot left for this vehicle type
    public event EventHandler<CapacityEventArgs>? SpaceAvailable;   // first slot freed after being full

    public string Name { get; }
    public string PricingName => _pricing.Name;
    public IReadOnlyList<Level> Levels => _levels;
    public IReadOnlyCollection<Ticket> OpenTickets => _openById.Values;
    public IReadOnlyList<Ticket> ClosedTickets => _closed;

    public ParkingLotService(string name, IEnumerable<Level> levels, IPricingStrategy pricing, IClock clock)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        Name = name;
        _pricing = pricing ?? throw new ArgumentNullException(nameof(pricing));
        _clock = clock ?? throw new ArgumentNullException(nameof(clock));
        _levels = levels.OrderBy(l => l.Number).ToList();
        if (_levels.Count == 0) throw new ArgumentException("A lot needs at least one level", nameof(levels));
        if (_levels.Select(l => l.Number).Distinct().Count() != _levels.Count)
            throw new ArgumentException("Level numbers must be unique", nameof(levels));
        _slotsById = _levels.SelectMany(l => l.Slots).ToDictionary(s => s.Id, StringComparer.OrdinalIgnoreCase);
    }

    public void ChangePricing(IPricingStrategy pricing) =>
        _pricing = pricing ?? throw new ArgumentNullException(nameof(pricing));

    public Result<Ticket> Park(Vehicle vehicle)
    {
        ArgumentNullException.ThrowIfNull(vehicle);
        if (_openByVehicle.TryGetValue(vehicle.Number, out var existing))
            return Result<Ticket>.Fail($"{vehicle.Number} is already parked at {existing.SlotId} (ticket {existing.Id})");

        ParkingSlot? slot = FindSlot(vehicle.Type);
        if (slot is null)
            return Result<Ticket>.Fail($"No free slot for a {vehicle.Type}");

        var before = FreeByType();
        slot.Assign(vehicle);
        var ticket = new Ticket($"T{++_ticketSequence:D4}", vehicle, slot, _clock.Now);
        _openById.Add(ticket.Id, ticket);
        _openByVehicle.Add(vehicle.Number, ticket);
        RaiseCapacityChanges(before);
        return Result<Ticket>.Ok(ticket);
    }

    public Result<Ticket> Exit(string ticketId)
    {
        if (string.IsNullOrWhiteSpace(ticketId) || !_openById.Remove(ticketId.Trim(), out var ticket))
            return Result<Ticket>.Fail($"No open ticket '{ticketId}'");

        var before = FreeByType();
        DateTime now = _clock.Now;
        ticket.Close(now, _pricing.Calculate(ticket.Vehicle.Type, ticket.EntryTime, now));   // ← Strategy
        _openByVehicle.Remove(ticket.Vehicle.Number);
        _slotsById[ticket.SlotId].Release();
        _closed.Add(ticket);
        RaiseCapacityChanges(before);
        return Result<Ticket>.Ok(ticket);
    }

    public string DescribeSlot(string slotId) => _slotsById[slotId].Describe();

    public Ticket? FindByVehicle(string number) =>
        _openByVehicle.GetValueOrDefault(Vehicle.Normalise(number));

    public int FreeSlotsFor(VehicleType type) =>
        _slotsById.Values.Count(s => s.IsFree && s.CanFit(type));

    public IReadOnlyList<LevelAvailability> Availability() =>
        _levels.Select(level => new LevelAvailability(level.Number,
                    Enum.GetValues<SlotSize>()
                        .Select(size => new SlotCount(size,
                            Free:  level.Slots.Count(s => s.Size == size && s.IsFree),
                            Total: level.Slots.Count(s => s.Size == size)))
                        .ToList()))
               .ToList();

    protected virtual void OnLotFull(CapacityEventArgs e) => LotFull?.Invoke(this, e);
    protected virtual void OnSpaceAvailable(CapacityEventArgs e) => SpaceAvailable?.Invoke(this, e);

    private Dictionary<VehicleType, int> FreeByType() =>
        Enum.GetValues<VehicleType>().ToDictionary(t => t, FreeSlotsFor);

    // One park can fill several types at once (a car taking the last Large slot also fills trucks)
    private void RaiseCapacityChanges(Dictionary<VehicleType, int> before)
    {
        foreach (var type in Enum.GetValues<VehicleType>())
        {
            int now = FreeSlotsFor(type);
            if (before[type] > 0 && now == 0)
                OnLotFull(new CapacityEventArgs(type, 0, _clock.Now));
            else if (before[type] == 0 && now > 0)
                OnSpaceAvailable(new CapacityEventArgs(type, now, _clock.Now));
        }
    }

    private ParkingSlot? FindSlot(VehicleType type) =>
        _levels.SelectMany(l => l.Slots)
               .Where(s => s.IsFree && s.CanFit(type))
               .OrderBy(s => s.Size)
               .ThenBy(s => s.Level)
               .FirstOrDefault();
}
""", "ParkingLot.Core/Services/ParkingLotService.cs (replaces Saturday's)")}
{table(["Saturday","Sunday"],[
["<code>CalculateFee</code> switch inside the service","<code>IPricingStrategy</code> injected; swap at runtime with <code>ChangePricing</code>"],
["Slots built with loops in Program.cs","<code>LotFactory.CreateLevels(layout, slotFactory)</code>"],
["No notifications","<code>LotFull</code> / <code>SpaceAvailable</code> events"],
["Program.cs does everything","Program.cs is a composition root"]])}

<h3>4. Observers in the app</h3>
{C(r"""
using ParkingLot.Core.Services;

namespace ParkingLot.App;

// Observer: the LED board at the entrance
public sealed class EntranceDisplay
{
    public void Attach(ParkingLotService lot)
    {
        lot.LotFull += OnLotFull;
        lot.SpaceAvailable += OnSpaceAvailable;
    }

    public void Detach(ParkingLotService lot)
    {
        lot.LotFull -= OnLotFull;
        lot.SpaceAvailable -= OnSpaceAvailable;
    }

    private void OnLotFull(object? sender, CapacityEventArgs e)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine($"  ▣ DISPLAY: {e.VehicleType.ToString().ToUpperInvariant()} PARKING FULL");
        Console.ResetColor();
    }

    private void OnSpaceAvailable(object? sender, CapacityEventArgs e) =>
        Console.WriteLine($"  ▣ DISPLAY: {e.VehicleType} parking open again ({e.FreeSlots} free)");
}
""", "ParkingLot.App/EntranceDisplay.cs")}

<h3>5. Program.cs as a composition root</h3>
{C(r"""
using ParkingLot.App;
using ParkingLot.Core;
using ParkingLot.Core.Models;
using ParkingLot.Core.Pricing;
using ParkingLot.Core.Services;
using ParkingLot.Core.Setup;

// ---------- Composition root: every concrete choice lives here ----------
var clock = new ManualClock(new DateTime(2026, 11, 13, 9, 0, 0));       // Fri 13 Nov 2026, 09:00

LevelConfig[] layout =
[
    new(Level: 1, Small: 2, Medium: 3, Large: 1),
    new(Level: 2, Small: 2, Medium: 3, Large: 1)
];
var levels = LotFactory.CreateLevels(layout, new EvSlotFactory(new StandardSlotFactory(), evLevel: 1));

var hourlyRates = new Dictionary<VehicleType, decimal>
    { [VehicleType.Bike] = 10m, [VehicleType.Car] = 40m, [VehicleType.Truck] = 100m };
var dailyRates = new Dictionary<VehicleType, decimal>
    { [VehicleType.Bike] = 50m, [VehicleType.Car] = 200m, [VehicleType.Truck] = 500m };

var pricingOptions = new Dictionary<string, IPricingStrategy>(StringComparer.OrdinalIgnoreCase)
{
    ["hourly"] = new HourlyPricing(hourlyRates),
    ["peak"]   = new PeakPricing(new HourlyPricing(hourlyRates)),
    ["flat"]   = new FlatRatePricing(dailyRates)
};

var lot = new ParkingLotService("City Centre Parking, Pune", levels, pricingOptions["peak"], clock);

new EntranceDisplay().Attach(lot);
lot.LotFull += (_, e) => Console.WriteLine($"  [SMS → manager] {e.VehicleType} slots full at {e.At:HH:mm}");
// ------------------------------------------------------------------------

int choice;
do
{
    Console.WriteLine($"\n==== {lot.Name} · {clock.Now:ddd dd MMM HH:mm} · {lot.PricingName} ====");
    Console.WriteLine("1) Availability  2) Park  3) Exit  4) Open tickets  5) Find vehicle  6) Advance clock  7) Pricing  0) Quit");
    choice = ConsoleInput.ReadChoice("Choose: ", 0, 7);
    try
    {
        switch (choice)
        {
            case 1: ShowAvailability(); break;
            case 2: Park(); break;
            case 3: Leave(); break;
            case 4:
                foreach (var t in lot.OpenTickets) Console.WriteLine($"  {t}");
                if (lot.OpenTickets.Count == 0) Console.WriteLine("  (no vehicles parked)");
                break;
            case 5:
                var found = lot.FindByVehicle(ConsoleInput.ReadText("Registration: "));
                Console.WriteLine(found is null ? "  Not in the lot" : $"  {found}");
                break;
            case 6:
                clock.Advance(TimeSpan.FromMinutes(ConsoleInput.ReadChoice("Minutes: ", 1, 7 * 24 * 60)));
                break;
            case 7: ChoosePricing(); break;
        }
    }
    catch (ArgumentException ex)
    {
        Console.WriteLine($"  ✗ {ex.Message}");
    }
} while (choice != 0);

void Park()
{
    var type = (VehicleType)(ConsoleInput.ReadChoice("1) Bike  2) Car  3) Truck: ", 1, 3) - 1);
    var vehicle = new Vehicle(ConsoleInput.ReadText("Registration: "), type);
    var r = lot.Park(vehicle);
    Console.WriteLine(r.Success
        ? $"  ✓ Ticket {r.Value!.Id}: {vehicle} → {lot.DescribeSlot(r.Value.SlotId)} at {r.Value.EntryTime:HH:mm}"
        : $"  ✗ {r.Error}");
}

void Leave()
{
    var r = lot.Exit(ConsoleInput.ReadText("Ticket id: "));
    if (!r.Success) { Console.WriteLine($"  ✗ {r.Error}"); return; }
    var t = r.Value!;
    Console.WriteLine($"  ✓ {t.Vehicle} left at {t.ExitTime:HH:mm} after {Format(t.Duration(clock.Now))} → ₹{t.Amount:N2} ({lot.PricingName})");
}

void ChoosePricing()
{
    string key = ConsoleInput.ReadText($"Pricing ({string.Join(", ", pricingOptions.Keys)}): ");
    if (pricingOptions.TryGetValue(key, out var strategy))
    {
        lot.ChangePricing(strategy);
        Console.WriteLine($"  ✓ Now using {strategy.Name}");
    }
    else Console.WriteLine($"  ✗ Unknown pricing '{key}'");
}

void ShowAvailability()
{
    Console.WriteLine($"  {"Level",-7}{"Small",-9}{"Medium",-9}{"Large",-9}");
    foreach (var level in lot.Availability())
    {
        Console.Write($"  L{level.Level,-6}");
        foreach (var c in level.Counts) Console.Write($"{c.Free + "/" + c.Total,-9}");
        Console.WriteLine();
    }
    Console.WriteLine("  Free for → " + string.Join("  ",
        Enum.GetValues<VehicleType>().Select(t => $"{t}: {lot.FreeSlotsFor(t)}")));
}

static string Format(TimeSpan d) => $"{(int)d.TotalHours}h {d.Minutes:D2}m";
""", "ParkingLot.App/Program.cs (replaces Saturday's)")}
{C(r"""
==== City Centre Parking, Pune · Fri 13 Nov 09:00 · Hourly + peak ×1.5 ====
Choose: 2
1) Bike  2) Car  3) Truck: 2
Registration: KA01AB1234
  ✓ Ticket T0001: Car KA01AB1234 → L1-M03 (EV charger) at 09:00
Choose: 2
1) Bike  2) Car  3) Truck: 3
Registration: MH12TR0001
  ✓ Ticket T0002: Truck MH12TR0001 → L1-L06 at 09:00
Choose: 2
1) Bike  2) Car  3) Truck: 3
Registration: MH12TR0002
  ▣ DISPLAY: TRUCK PARKING FULL
  [SMS → manager] Truck slots full at 09:00
  ✓ Ticket T0003: Truck MH12TR0002 → L2-L06 at 09:00
Choose: 2
1) Bike  2) Car  3) Truck: 3
Registration: GJ05TR7788
  ✗ No free slot for a Truck
Choose: 6
Minutes: 150
Choose: 3
Ticket id: T0001
  ✓ Car KA01AB1234 left at 11:30 after 2h 30m → ₹120.00 (Hourly + peak ×1.5)
Choose: 3
Ticket id: T0002
  ▣ DISPLAY: Truck parking open again (1 free)
  ✓ Truck MH12TR0001 left at 11:30 after 2h 30m → ₹300.00 (Hourly + peak ×1.5)
""", lang="text")}

<h3>6. Try to break it</h3>
{table(["Scenario","Expected"],[
["Park KA01AB1234 twice","\"KA01AB1234 is already parked at L1-M03 (ticket T0001)\""],
["Registration <code>HELLO</code> or empty","✗ not a valid registration number / Please enter a value"],
["Registration <code>ka-01-ab-1234</code>","Accepted and normalised to KA01AB1234"],
["Exit T9999, or exit T0001 twice","\"No open ticket 'T9999'\" / second exit fails the same way"],
["5 bikes when 4 Small slots exist","5th bike gets L1-M03 (overflow to the smallest larger slot)"],
["Park 2 trucks","LotFull(Truck) fires once: display + manager SMS; 3rd truck rejected"],
["Park 8 cars (6 Medium slots + 2 Large)","Cars 7 and 8 take the Large slots; the 8th raises LotFull for both Car and Truck, though no truck parked"],
["Exit one truck when trucks were full","SpaceAvailable(Truck, 1 free)"],
["Car in and out within 8 minutes (hourly or peak)","₹0 grace"],
["Car Fri 18:00 → 20:00 with peak pricing","₹120 (₹80 × 1.5)"],
["Switch to flat, car stays 26 h","₹400 (2 started days)"],
["Pricing key <code>FLAT</code> (upper case)","Accepted — case-insensitive dictionary"],
["<code>LevelConfig</code> with level 1 listed twice","ArgumentException at startup: \"Level 1 is configured twice\""],
["<code>new LevelConfig(3, 0, 0, 0)</code>","ArgumentException from Level: \"Level 3 has no slots\""],
["<code>new PeakPricing(inner, 0.8m)</code>","ArgumentOutOfRangeException: multiplier must be at least 1"],
["<code>clock.Advance(TimeSpan.FromMinutes(-5))</code> in code","ArgumentOutOfRangeException: time can't go backwards"]])}

<h3>7. README and push</h3>
{C(r"""
# Parking Lot System

Micro-project 7 of my .NET full-stack roadmap (Week 9: SOLID and design patterns).

## Features
- Multi-level lot with Small / Medium / Large slots; bikes, cars and trucks
- Smallest-fit allocation (lowest level first), overflow to larger slots
- Tickets with entry/exit times; fees on exit; live availability per level
- Pricing strategies: hourly (with grace period), flat per day, peak/weekend surcharge
- Slots created by a factory from a layout configuration (EV bays on level 1)
- "Lot full" / "space available" alerts via events (entrance display, manager SMS)

## Design
| Pattern | Where |
|---|---|
| Strategy | `IPricingStrategy`: `HourlyPricing`, `FlatRatePricing`, `PeakPricing` |
| Decorator | `PeakPricing` wraps another strategy; `EvSlotFactory` wraps a slot factory |
| Factory | `ISlotFactory`, `LotFactory.CreateLevels(LevelConfig[])` |
| Observer | `ParkingLotService.LotFull` / `SpaceAvailable` events |
| DIP / DI | `IClock`, strategies and factories chosen in the composition root (Program.cs) |

## Run
```bash
dotnet run --project ParkingLot.App
```
""", "README.md", lang="markdown")}
{C(r"""
git init                                    # if this is a new repo
dotnet new gitignore
git add .
git commit -m "Parking lot: levels, slots, tickets, availability"
# after Sunday's refactor
git add .
git commit -m "Parking lot: pricing strategies, slot factory, lot-full observers"
git branch -M main
git remote add origin https://github.com/<you>/parking-lot.git
git push -u origin main
""", lang="bash")}

<h3>8. Week 9 revision checklist</h3>
<ul>
<li>State each SOLID principle in one sentence and give a violation and a fix</li>
<li>SRP: reasons to change; the InvoiceService split; thin orchestrators</li>
<li>OCP: rules as classes; when a switch is fine; delegate tables</li>
<li>LSP: Rectangle/Square; ReadOnlyCollection as ICollection; contract rules</li>
<li>ISP: role interfaces (IPrinter, IScanner); DIP: who owns the interface</li>
<li>DI: constructor injection, composition root, Singleton/Scoped/Transient, captive dependencies, ValidateScopes</li>
<li>Singleton with Lazy&lt;T&gt;; why DI singletons are preferred</li>
<li>Simple factory vs Factory Method vs Abstract Factory; fluent Builder with validation</li>
<li>Strategy selected via dictionary/IEnumerable/keyed services; Observer via events and IObservable&lt;T&gt;</li>
<li>Repository and Unit of Work; how DbContext maps onto them</li>
<li>Decorator vs Adapter vs Proxy vs Facade; patterns inside .NET (streams, middleware, handlers, iterators, ILogger)</li>
<li>Parking lot: draw the class diagram from memory in 10 minutes</li>
</ul>

<h3>9. Quick quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
var rates = new Lazy<string>(() => { Console.Write("load "); return "GST"; });
Console.Write("start ");
Console.Write(rates.Value);
Console.Write(rates.Value);
""")}<b>start load GSTGST</b>. The factory runs on first access to <code>Value</code>, once; the second access returns the cached value.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddScoped<Cart>();
using var provider = services.BuildServiceProvider();
using var s1 = provider.CreateScope();
using var s2 = provider.CreateScope();

var a = s1.ServiceProvider.GetRequiredService<Cart>();
var b = s1.ServiceProvider.GetRequiredService<Cart>();
var c = s2.ServiceProvider.GetRequiredService<Cart>();
Console.WriteLine($"{ReferenceEquals(a, b)} {ReferenceEquals(a, c)}");

class Cart { }
""")}<b>True False</b>. Scoped means one instance per scope: same within <code>s1</code>, different in <code>s2</code>.</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
IMessage msg = new Twice(new Star(new Hello()));
Console.WriteLine(msg.Text());

interface IMessage { string Text(); }
class Hello : IMessage { public string Text() => "hi"; }
class Star(IMessage inner) : IMessage { public string Text() => "*" + inner.Text(); }
class Twice(IMessage inner) : IMessage { public string Text() => inner.Text() + inner.Text(); }
""")}<b>*hi*hi</b>. Decorators apply from the inside out: Star gives "*hi", Twice repeats it. Swapping the order (<code>new Star(new Twice(...))</code>) gives "*hihi".</details>
<details><summary>Q4. Does this compile, and what happens when it runs?</summary>
{C(r"""
using System.Collections.ObjectModel;

ICollection<int> scores = new ReadOnlyCollection<int>(new List<int> { 90 });
scores.Add(75);
Console.WriteLine(scores.Count);
""")}<b>It compiles, then throws NotSupportedException</b> on <code>Add</code>. ReadOnlyCollection implements ICollection&lt;T&gt; explicitly — a textbook LSP violation in the BCL. Use <code>IReadOnlyCollection&lt;int&gt;</code> to get a compile-time error instead.</details>
<details><summary>Q5. What prints?</summary>
{C(r"""
var lot = new Lot();
EventHandler alert = (_, _) => Console.Write("FULL ");
lot.Full += alert;
lot.Full += alert;
lot.Full -= alert;
lot.Raise();

class Lot
{
    public event EventHandler? Full;
    public void Raise() => Full?.Invoke(this, EventArgs.Empty);
}
""")}<b>FULL</b> (once). Subscribing the same delegate twice adds it twice; <code>-=</code> removes only the last occurrence.</details>

<div class="note tip"><b>Next week:</b> Week 10 — Git in depth (branching, merging, rebase, resolving conflicts, pull requests and a clean commit history) and the <b>Phase 1 exit check</b>: a timed review of Weeks 1–9 (C# fundamentals, OOP, collections, LINQ, SOLID and patterns) to confirm you're ready for Phase 2.</div>
''',
iqs=[("Basic","How did you apply the Strategy pattern in the parking lot?","Fee calculation is behind IPricingStrategy with HourlyPricing, FlatRatePricing and PeakPricing. The service only calls Calculate on whichever strategy it was given, so a new tariff (e.g. monthly pass) is a new class and one line in the composition root."),
("Basic","Why did you use events for \"lot full\" instead of printing from the service?","The service shouldn't know about displays, SMS or logging. It announces a fact (no slots left for trucks) and any number of observers react. New reactions don't change the service, and it stays testable."),
("Intermediate","PeakPricing wraps another IPricingStrategy. Which pattern is that, and why is it useful?","It's a Decorator applied to a strategy: same interface, added behaviour (a multiplier). It composes with any base tariff — peak hourly or peak flat — without writing a PeakHourlyPricing and PeakFlatPricing class for every combination."),
("Intermediate","What would change to support online pre-booking and multiple entry gates?","Add a Reservation entity and a slot state (Free, Reserved, Occupied); make allocation honour reservations; protect find-and-assign with a lock or a database transaction with a conditional update; move storage behind repositories and a unit of work; and expose Park/Exit through a Web API (Phase 2).")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","SOLID: Single Responsibility and Open/Closed","SRP &amp; OCP","Splitting an InvoiceService, discount rules open for extension, when a switch is fine.","2 hrs"),
 (2,"TUE","SOLID: Liskov, Interface Segregation, Dependency Inversion and DI","LSP · ISP · DIP · DI","Rectangle/Square, role interfaces, composition root, lifetimes, ServiceCollection.","2 hrs"),
 (3,"WED","Creational patterns: Singleton, Factories, Builder","Creational patterns","Lazy&lt;T&gt; singletons vs DI, simple/Factory Method/Abstract Factory, fluent builders.","2 hrs"),
 (4,"THU","Strategy, Observer, Repository and Unit of Work","Strategy · Observer · UoW","Shipping strategies via dictionary and DI, events vs IObservable, all-or-nothing saves.","2 hrs"),
 (5,"FRI","Decorator, Adapter and patterns inside .NET","Decorator &amp; Adapter","Caching decorators, wrapping a payment SDK, streams, middleware, HttpClient handlers.","2 hrs"),
 (6,"SAT","Micro-project 7: Parking lot system","Project: parking lot","Requirements, class diagram, levels, sized slots, tickets, allocation, availability.","4 hrs"),
 (7,"SUN","Parking lot patterns, README and revision","Patterns &amp; revision","Pricing strategies, slot factory, lot-full observers, try-to-break table, quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week09.html", 9,
      "Week 9 — SOLID and design patterns", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 9 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 7"],
      "You can write C#; this week is about writing C# that is easy to change. You'll learn the five SOLID principles through before/after refactors, wire dependencies with constructor injection and the .NET DI container, and add the most-used design patterns to your vocabulary — and spot them inside .NET itself. The week ends with the classic interview LLD question: a parking lot system, designed first and then built with Strategy, Factory and Observer.",
      cards, days)
print("built")
