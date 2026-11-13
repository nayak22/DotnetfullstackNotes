import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Threads, tasks and the thread pool",
"Understand what a thread is, why .NET code almost always uses Task instead, and how to tell CPU-bound work (needs a core) from I/O-bound work (needs waiting) — the single most important distinction in async programming.",
[("Process","A running program with its own memory space. One process contains one or more threads."),
("Thread","An independent path of execution with its own stack. The OS scheduler decides which threads run on which CPU cores."),
("Foreground / background thread","The process stays alive until all foreground threads finish; background threads are killed when the process exits. Thread-pool threads are background threads."),
("Context switch","The OS pausing one thread and resuming another on a core. Cheap, but not free; thousands of threads mean lots of switching."),
("Thread pool","A shared set of reusable worker threads managed by .NET. It grows and shrinks based on load so you don't create threads yourself."),
("Task","An object representing an operation that will complete in the future: it has a status, may hold an exception, and can be awaited."),
("Task&lt;TResult&gt;","A Task that also produces a value of type TResult when it completes."),
("Task.Run","Queues a delegate to run on a thread-pool thread and returns a Task for it. Use it for CPU-bound work."),
("CPU-bound","Work limited by processor speed: calculations, compression, image resizing, parsing huge files in memory."),
("I/O-bound","Work that mostly waits for something outside the CPU: network, disk, database. No thread needs to be busy while waiting."),
("Concurrency","Several operations in progress during the same period of time (they may take turns on one core)."),
("Parallelism","Several operations literally executing at the same instant on different cores. A subset of concurrency."),
("TaskStatus","The lifecycle state of a task: Created, WaitingForActivation, WaitingToRun, Running, WaitingForChildrenToComplete (rare: attached child tasks), RanToCompletion, Faulted, Canceled."),
("AggregateException","An exception that wraps one or more inner exceptions. Blocking APIs like Wait() and .Result throw it; await unwraps it."),
("ValueTask&lt;T&gt;","A struct alternative to Task&lt;T&gt; that avoids a heap allocation when the result is often available immediately.")],
["You will rarely write <code>new Thread(...)</code> in modern .NET. Use <code>Task</code> and <code>async</code>/<code>await</code>.",
"<code>Task.Run</code> is for CPU-bound work. For I/O, call the library's async method (<code>ReadAllTextAsync</code>, <code>GetAsync</code>, <code>ToListAsync</code>).",
"While an I/O operation is in flight, no thread is sitting there waiting for it. That's why async scales.",
"A task that throws doesn't crash anything immediately: the exception is stored inside the task until someone awaits it.",
"<code>await</code> rethrows the original exception; <code>.Wait()</code> and <code>.Result</code> wrap it in AggregateException (and block a thread).",
"Default to <code>Task</code>/<code>Task&lt;T&gt;</code>. Reach for <code>ValueTask</code> only on hot paths that usually complete synchronously."],
f'''
<h3>1. Threads: the raw building block</h3>
<p>A thread is the unit the operating system schedules onto a CPU core. Your console app starts with one (the main thread). You <i>can</i> create more yourself, and seeing it once makes everything else this week easier to picture.</p>
{C(r"""
Console.WriteLine($"Main thread id: {Environment.CurrentManagedThreadId}");

var printer = new Thread(() =>
{
    for (int i = 1; i <= 3; i++)
    {
        Console.WriteLine($"  Printing invoice INV-{i:000} on thread {Environment.CurrentManagedThreadId}");
        Thread.Sleep(200);                     // blocks THIS thread only
    }
})
{
    Name = "InvoicePrinter",
    IsBackground = false                       // foreground (the default): the process waits for it
};

printer.Start();
Console.WriteLine("Main thread carries on...");
printer.Join();                                // block the main thread until the printer finishes
Console.WriteLine("All invoices printed");

// Main thread id: 1
// Main thread carries on...                   ← these two lines can appear in either order:
//   Printing invoice INV-001 on thread 10     ← the OS decides who runs first (id varies)
//   Printing invoice INV-002 on thread 10
//   Printing invoice INV-003 on thread 10
// All invoices printed
""", "ThreadDemo.cs")}
<p>Why not do this everywhere? Each thread reserves its own stack (around 1 MB or more of address space), takes time to create, and adds context switching. A web server handling 5,000 requests with 5,000 threads would spend more effort juggling threads than doing work. The thread pool and tasks solve this.</p>

<h3>2. The thread pool and Task</h3>
<p>The <b>thread pool</b> keeps a small set of worker threads alive and hands them short pieces of work. A <b>Task</b> is the object you get back: it tells you when the work is done, carries its result or exception, and can be awaited.</p>
{C(r"""
// Old style: queue work to the pool. No result, no way to await it, exceptions crash the process.
ThreadPool.QueueUserWorkItem(_ =>
    Console.WriteLine($"Pool thread {Environment.CurrentManagedThreadId}"));

// Modern style: Task.Run queues the same kind of work but gives you a Task back
Task log = Task.Run(() =>
    Console.WriteLine($"Task on thread {Environment.CurrentManagedThreadId}, " +
                      $"pool thread? {Thread.CurrentThread.IsThreadPoolThread}"));   // True
await log;                                     // wait without blocking (Tuesday explains how)

// Task<T>: the work produces a value
Task<decimal> totalTask = Task.Run(() =>
{
    decimal sum = 0;
    for (int i = 1; i <= 1_000_000; i++) sum += i % 1000 * 1.18m;   // CPU work: price incl. 18% GST
    return sum;
});

decimal total = await totalTask;
Console.WriteLine($"Total: ₹{total:N2}");
""", "TaskBasics.cs")}
{table(["","new Thread","ThreadPool.QueueUserWorkItem","Task.Run / async"],[
["Creates a thread","Yes, every time","No, reuses pool threads","No, reuses pool threads (async I/O may use none)"],
["Returns a result","No (use shared fields)","No","Yes, <code>Task&lt;T&gt;</code>"],
["Exceptions","Unhandled → process crashes","Unhandled → process crashes","Stored in the task, rethrown on await"],
["Can be awaited / combined","No (only Join)","No","Yes: await, WhenAll, WhenAny, cancellation"],
["Use today for","Rare: a dedicated long-running loop with special needs","Almost never","Everything else"]])}
{tip("For a truly long-running background loop (a queue consumer that runs for the whole app lifetime) you can use <code>Task.Factory.StartNew(..., TaskCreationOptions.LongRunning)</code>, which gives it a dedicated thread instead of tying up a pool thread. In ASP.NET Core you'll use <code>BackgroundService</code> instead (later in the course).")}

<h3>3. CPU-bound vs I/O-bound — and concurrency vs parallelism</h3>
<p>Ask one question about any slow operation: <i>is the CPU busy, or is it waiting?</i></p>
{C(r"""
// CPU-bound: the CPU is busy the whole time → move it off the current thread with Task.Run
static decimal CalculateGst(IReadOnlyList<decimal> amounts)
{
    decimal gst = 0;
    foreach (decimal a in amounts) gst += Math.Round(a * 0.18m, 2);
    return gst;
}

List<decimal> amounts = Enumerable.Range(1, 2_000_000).Select(i => (decimal)(i % 5000)).ToList();
decimal gst = await Task.Run(() => CalculateGst(amounts));   // keeps a UI responsive while a core crunches
Console.WriteLine($"GST: ₹{gst:N2}");

// I/O-bound: the CPU is idle, we're WAITING on disk or network → call the async API directly
await File.WriteAllTextAsync("invoices.csv", "INV-001,Asha Rao,1180.00\n");
string csv = await File.ReadAllTextAsync("invoices.csv");   // no thread is blocked while the disk works
await Task.Delay(500);                                      // a timer, not a sleeping thread

// ❌ Wrapping I/O in Task.Run: a pool thread now sits blocked waiting for the disk
string wasteful = await Task.Run(() => File.ReadAllText("invoices.csv"));
""", "CpuVsIo.cs")}
{table(["","CPU-bound","I/O-bound"],[
["Examples","GST on 2 million lines, PDF generation, image resize, hashing passwords","HTTP calls, database queries, reading files, sending email"],
["Bottleneck","Processor cores","Network / disk / remote service"],
["Right tool","<code>Task.Run</code>, <code>Parallel.For</code> (Friday)","The library's <code>...Async</code> method + <code>await</code>"],
["More concurrency helps until…","You run out of cores","The remote side or bandwidth is saturated"],
["Threads used while waiting","One per running piece of work","Zero"]])}
{table(["","Concurrency","Parallelism"],[
["Meaning","Many things <i>in progress</i> over the same period","Many things <i>executing</i> at the same instant"],
["Needs multiple cores?","No — one core can interleave","Yes"],
["Kitchen analogy","One cook with three pans: stirs one while the others simmer","Three cooks, each at their own stove"],
["Typical .NET tool","<code>async</code>/<code>await</code>, <code>Task.WhenAll</code>","<code>Parallel.For</code>, <code>Task.Run</code> on many items, PLINQ"]])}
<p>Saturday's downloader is the perfect example of concurrency without needing parallelism: 20 downloads can all be "in progress" while the CPU is almost idle.</p>

<h3>4. Task states and exceptions inside tasks</h3>
{C(r"""
Task<int> slow = Task.Run(async () => { await Task.Delay(300); return 42; });
Console.WriteLine(slow.Status);              // WaitingForActivation — not finished yet
Console.WriteLine(slow.IsCompleted);         // False
int answer = await slow;
Console.WriteLine(slow.Status);              // RanToCompletion
Console.WriteLine(slow.IsCompletedSuccessfully);   // True
""")}
{table(["Status","Meaning","IsCompleted"],[
["Created","Built with <code>new Task(...)</code> but not started (rare; prefer Task.Run)","False"],
["WaitingForActivation","Waiting for something internal (typical for async methods)","False"],
["WaitingToRun","Scheduled on the pool, not yet picked up","False"],
["Running","Executing right now","False"],
["RanToCompletion","Finished successfully; result available","True"],
["Faulted","Finished by throwing; <code>task.Exception</code> holds an AggregateException","True"],
["Canceled","Finished because cancellation was requested (Wednesday)","True"]])}
{C(r"""
static async Task<decimal> GetGstRateAsync(string stateCode)
{
    await Task.Delay(50);
    throw new KeyNotFoundException($"No GST registration for state {stateCode}");
}

Task<decimal> rateTask = GetGstRateAsync("XX");  // nothing thrown HERE — the exception goes into the task
await Task.Delay(100);
Console.WriteLine(rateTask.Status);              // Faulted
Console.WriteLine(rateTask.Exception!.GetType().Name);              // AggregateException
Console.WriteLine(rateTask.Exception.InnerException!.Message);      // No GST registration for state XX

try { await rateTask; }                          // await unwraps → the ORIGINAL exception type
catch (KeyNotFoundException ex) { Console.WriteLine($"await threw {ex.GetType().Name}"); }

try { rateTask.Wait(); }                         // blocking APIs wrap it
catch (AggregateException ex) { Console.WriteLine($"Wait() threw AggregateException with {ex.InnerExceptions.Count} inner"); }

// await threw KeyNotFoundException
// Wait() threw AggregateException with 1 inner
""", "TaskExceptions.cs")}
{warn("A faulted task that nobody ever awaits or inspects is an <b>unobserved exception</b>: the error silently disappears (the <code>TaskScheduler.UnobservedTaskException</code> event fires much later, when the GC collects the task). Always await the tasks you start, or deliberately log their failures.", "Gotcha")}
<p><code>AggregateException</code> exists because one task can represent many operations (e.g. <code>Task.WhenAll</code>, Wednesday), so it can hold many failures. Use <code>ex.Flatten()</code> when aggregates are nested, and <code>ex.InnerExceptions</code> to see them all.</p>

<h3>5. ValueTask&lt;T&gt; — awareness, not a default</h3>
<p>Every <code>Task&lt;T&gt;</code> is a heap object. If a method is called millions of times and usually has the answer ready (a cache hit), those allocations add up. <code>ValueTask&lt;T&gt;</code> is a struct that can hold the result directly, and only wraps a real Task when work is actually pending.</p>
{C(r"""
var cache = new GstRateCache();
Console.WriteLine(await cache.GetRateAsync("0401"));   // 0.05 (slow path, 100 ms)
Console.WriteLine(await cache.GetRateAsync("0401"));   // 0.05 (fast path, no allocation)

public class GstRateCache
{
    // Single-threaded demo; Friday shows ConcurrentDictionary for shared caches
    private readonly Dictionary<string, decimal> _rates = new(StringComparer.OrdinalIgnoreCase);

    public ValueTask<decimal> GetRateAsync(string hsnCode)
    {
        if (_rates.TryGetValue(hsnCode, out decimal rate))
            return ValueTask.FromResult(rate);                 // cache hit: no allocation, completes synchronously

        return new ValueTask<decimal>(LoadAndCacheAsync(hsnCode));   // cache miss: wrap a real Task
    }

    private async Task<decimal> LoadAndCacheAsync(string hsnCode)
    {
        await Task.Delay(100);                                 // pretend: call the GST rate service
        decimal rate = hsnCode.StartsWith("04") ? 0.05m : 0.18m;   // dairy 5%, everything else 18%
        _rates[hsnCode] = rate;
        return rate;
    }
}
""", "GstRateCache.cs")}
{table(["Rule for ValueTask","Why"],[
["Await it exactly once","It may be backed by a pooled object that gets reused after the first await"],
["Never await it concurrently from two places","Same reason; behaviour is undefined"],
["Don't call <code>.Result</code> unless <code>IsCompletedSuccessfully</code>","Blocking on a pending ValueTask isn't supported"],
["Need any of the above? Call <code>.AsTask()</code> once","Converts it to a normal Task you can await many times or pass to WhenAll"]])}
{tip("You'll mostly <i>consume</i> ValueTask from framework APIs (<code>Stream.ReadAsync(Memory&lt;byte&gt;)</code>, <code>IAsyncEnumerator.MoveNextAsync</code>, <code>DbContext.FindAsync</code>). Just await it directly and you're following every rule.")}
''',
["Using <code>Task.Run</code> to \"make I/O async\" — it just blocks a pool thread instead of the caller's thread.",
"Creating <code>new Thread</code> for short jobs instead of using tasks and the pool.",
"Starting a task and never awaiting it, so its exception is silently lost.",
"Catching <code>AggregateException</code> around <code>await</code> (await throws the inner exception) or the specific type around <code>.Wait()</code> (it throws AggregateException).",
"Returning ValueTask everywhere \"for performance\" and then awaiting it twice."],
("35 min", ["Create 2,000,000 random invoice amounts. Time computing their total GST on the current thread vs <code>await Task.Run(...)</code> with <code>Stopwatch</code>. Explain why the time is about the same (and what Task.Run <i>does</i> buy you).",
"Write <code>async Task&lt;string&gt; LoadCustomerAsync(int id)</code> that throws for negative ids. Start it, print <code>Status</code> before and after a delay, then catch the exception with await and separately with <code>.Wait()</code>; print both exception types.",
"Classify 10 operations from your bank and library projects (statement PDF, sending an SMS alert, sorting 1 lakh transactions, reading a CSV, calling a PIN-code API…) as CPU- or I/O-bound and write which API you'd use for each."]),
[("Why does Task.Run not make a database call faster?","The call is I/O-bound: the time is spent waiting for the database. Task.Run only moves the waiting onto a pool thread. Use the async database API so no thread waits at all."),
("What does await do with an exception stored in a faulted task?","It rethrows the original exception (first inner exception), with its stack trace preserved, so you catch the real type like KeyNotFoundException."),
("When is ValueTask&lt;T&gt; worth using?","On hot paths that very often complete synchronously (cache hits, buffered reads), where avoiding a Task allocation per call measurably helps.")],
[("Basic","What is the difference between a Thread and a Task?","A Thread is an OS-level execution path you create and manage directly. A Task is a higher-level promise of a future result: it's usually run on pooled threads (or, for async I/O, no thread at all while waiting), carries its result and exceptions, supports cancellation, and composes with await, WhenAll and WhenAny. Modern .NET code uses tasks."),
("Basic","What is the difference between CPU-bound and I/O-bound work, and when should you use Task.Run?","CPU-bound work keeps a core busy (calculations, compression); I/O-bound work waits on network, disk or a database. Use Task.Run to offload CPU-bound work (for example, to keep a UI thread responsive). For I/O-bound work, await the library's async API directly; wrapping it in Task.Run wastes a thread."),
("Basic","Explain concurrency vs parallelism.","Concurrency means multiple operations are in progress during overlapping time periods, possibly interleaved on one core (e.g. 50 awaited HTTP calls). Parallelism means operations execute at literally the same time on multiple cores (e.g. Parallel.For over a big array). Parallelism is one way of achieving concurrency."),
("Intermediate","What happens when code inside a Task throws?","The exception is caught by the task infrastructure and stored; the task moves to Faulted and task.Exception holds an AggregateException. Awaiting the task rethrows the original inner exception; .Wait() and .Result throw the AggregateException. If nobody observes it, the error is lost and only the UnobservedTaskException event reports it later."),
("Intermediate","What is ValueTask and what are its restrictions?","A struct that can hold a result directly or wrap a Task/IValueTaskSource, avoiding allocations when an async method usually completes synchronously. Restrictions: await it only once, never concurrently, don't block on it before it's complete; call AsTask() if you need Task semantics. Default to Task unless profiling shows allocation pressure."),
("Intermediate","Why is Task.Run around I/O an anti-pattern in ASP.NET Core?","ASP.NET Core requests already run on pool threads. Task.Run just switches to another pool thread, which then blocks on synchronous I/O, so you use two threads instead of zero and add scheduling overhead. Under load this leads to thread-pool starvation. Use true async APIs end to end.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "async/await: how it works and how to use it well",
"Know exactly what happens when execution hits an await, what the compiler generates, where the code after an await runs, and the handful of rules (async all the way, no .Result, no async void, ConfigureAwait in libraries) that prevent deadlocks and crashes.",
[("async","A modifier that lets a method use await. It does not by itself make anything run on another thread."),
("await","Pauses the method until the awaited task completes, <i>without blocking the thread</i>; then resumes with the result or rethrows the exception."),
("Awaitable","Anything with a GetAwaiter() method: Task, Task&lt;T&gt;, ValueTask, Task.Yield(), and more."),
("Continuation","The rest of the method after an await, packaged up to run when the awaited operation completes."),
("State machine","The struct/class the compiler generates for an async method; it stores locals as fields and a state number recording which await to resume after."),
("SynchronizationContext","An object that says where continuations should run, e.g. \"back on the UI thread\". Console apps and ASP.NET Core don't have one."),
("TaskScheduler","Decides where tasks run when there's no SynchronizationContext; the default schedules onto the thread pool."),
("ConfigureAwait(false)","Tells await not to capture the current SynchronizationContext, so the continuation can run on any pool thread."),
("Sync-over-async","Blocking on async code with .Result, .Wait() or GetAwaiter().GetResult(). Causes deadlocks and thread starvation."),
("Async all the way","If a method awaits, its caller should be async and await it too, up to the entry point (Main, controller action, event handler)."),
("async void","An async method returning void. Can't be awaited; its exceptions are raised directly on the SynchronizationContext or thread pool, usually crashing the app."),
("Fire-and-forget","Starting async work without awaiting it. Dangerous unless failures are explicitly handled."),
("Task.CompletedTask / Task.FromResult","Ready-made completed tasks for implementing async signatures synchronously.")],
["An async method runs <b>synchronously</b> until the first await on an <i>incomplete</i> task. Only then does it return to its caller.",
"Awaiting an already-completed task continues immediately on the same thread — no pause, no thread switch.",
"After an await the code may resume on a different thread (console, ASP.NET Core) or back on the UI thread (WinForms, WPF, MAUI).",
"Name async methods with the <code>Async</code> suffix and return <code>Task</code>, <code>Task&lt;T&gt;</code> or <code>ValueTask&lt;T&gt;</code>.",
"Libraries: <code>ConfigureAwait(false)</code> on every await. ASP.NET Core and console app code: not needed.",
"<code>async void</code> only for event handlers. Everything else returns Task."],
f'''
<h3>1. What await actually does</h3>
{C(r"""
Console.WriteLine($"1. Before call     thread {Environment.CurrentManagedThreadId}");
string report = await BuildSalesReportAsync();
Console.WriteLine($"4. Got the report  thread {Environment.CurrentManagedThreadId}: {report}");

static async Task<string> BuildSalesReportAsync()
{
    Console.WriteLine($"2. Method started  thread {Environment.CurrentManagedThreadId}");
    await Task.Delay(500);         // incomplete task → method pauses here and RETURNS to the caller
    Console.WriteLine($"3. Method resumed  thread {Environment.CurrentManagedThreadId}");
    return "Sales ₹4,52,000";
}

// 1. Before call     thread 1
// 2. Method started  thread 1     ← synchronous up to the first real await
// 3. Method resumed  thread 6     ← console app: no SynchronizationContext → any pool thread
// 4. Got the report  thread 6: Sales ₹4,52,000
""", "AwaitDemo.cs")}
<p>Step by step, when execution reaches <code>await someTask</code>:</p>
<ol>
<li>Check <code>someTask.IsCompleted</code>. If it's already done, take the result and keep going on the same thread — no pause at all.</li>
<li>If not, capture the current <b>SynchronizationContext</b> (if any), register "the rest of this method" as a <b>continuation</b> on the task, and <b>return</b> an incomplete Task to the caller. The thread is now free to do other work (serve another request, repaint the window).</li>
<li>When the operation finishes (a timer fires, a network packet arrives), the continuation is scheduled: back on the captured context if there was one, otherwise on a thread-pool thread.</li>
<li>The method resumes after the await with its locals intact, either getting the result or having the original exception rethrown.</li>
</ol>
{tip("There's no thread sitting inside <code>Task.Delay(500)</code> or a pending HTTP call. The OS notifies .NET when the I/O completes. That's how a server with 30 pool threads can have 10,000 requests waiting on a database at once.")}

<h3>2. What the compiler generates</h3>
<p>The compiler rewrites every async method into a <b>state machine</b>. Locals become fields (so they survive the pause), and each await becomes a numbered resume point. You never write this, but knowing its shape explains every behaviour above.</p>
{C(r"""
// What you write
public async Task<decimal> GetInvoiceTotalAsync(int invoiceId)
{
    Invoice invoice = await _repository.LoadAsync(invoiceId);
    decimal rate = await _gst.GetRateAsync(invoice.StateCode);
    return invoice.Amount * (1 + rate);
}

// Roughly what the compiler generates (simplified pseudo-code, not compilable)
struct GetInvoiceTotalAsync_StateMachine : IAsyncStateMachine
{
    public int state;                                 // -1 running, 0 = paused at await #1, 1 = at await #2
    public AsyncTaskMethodBuilder<decimal> builder;   // creates the Task the caller receives, completes it later
    public int invoiceId;                             // parameters and locals are FIELDS now
    private Invoice invoice;
    private TaskAwaiter<Invoice> awaiter1;
    private TaskAwaiter<decimal> awaiter2;

    public void MoveNext()                            // called once to start, then once per resume
    {
        try
        {
            if (state == 0) goto Resume1;
            if (state == 1) goto Resume2;

            awaiter1 = _repository.LoadAsync(invoiceId).GetAwaiter();
            if (!awaiter1.IsCompleted)
            {
                state = 0;
                builder.AwaitUnsafeOnCompleted(ref awaiter1, ref this);   // "call MoveNext again when done"
                return;                                                     // ← the thread leaves here
            }
        Resume1:
            invoice = awaiter1.GetResult();           // returns the value or rethrows the original exception

            awaiter2 = _gst.GetRateAsync(invoice.StateCode).GetAwaiter();
            if (!awaiter2.IsCompleted) { state = 1; builder.AwaitUnsafeOnCompleted(ref awaiter2, ref this); return; }
        Resume2:
            decimal rate = awaiter2.GetResult();
            builder.SetResult(invoice.Amount * (1 + rate));   // completes the caller's Task<decimal>
        }
        catch (Exception ex)
        {
            builder.SetException(ex);                 // exceptions go INTO the task (Monday) instead of propagating
        }
    }
}
""", "StateMachine (pseudo-code)")}
<p>Consequences you can now explain: exceptions end up inside the returned task; an async method with no awaits runs fully synchronously (and the compiler warns CS1998); <code>ref</code>/<code>out</code> parameters aren't allowed in async methods (they can't be stored as fields); and in Release builds the state machine is a struct, so the fast path where everything completes synchronously allocates nothing extra.</p>

<h3>3. SynchronizationContext and ConfigureAwait(false)</h3>
<p>UI frameworks only let the UI thread touch controls, so they install a SynchronizationContext that sends continuations back to the UI thread. That's what makes this code safe:</p>
{C(r"""
// WinForms / WPF: the click handler starts on the UI thread
private async void btnLoadOrders_Click(object sender, EventArgs e)   // async void is fine: it's an event handler
{
    lblStatus.Text = "Loading orders...";
    Order[] orders = await _ordersApi.GetTodayAsync();   // UI thread is free while waiting → window stays responsive
    gridOrders.DataSource = orders;                       // resumed ON THE UI THREAD via the captured context
    lblStatus.Text = $"{orders.Length} orders";
}
""", "OrdersForm.cs (WinForms fragment)")}
{table(["App type","SynchronizationContext?","Code after await runs on…"],[
["WinForms, WPF, MAUI","Yes (UI context)","The UI thread"],
["Classic ASP.NET (System.Web, .NET Framework)","Yes (request context)","The request's context, one thread at a time"],
["Blazor Server / interactive server components","Yes (renderer context)","The renderer's context (Blazor WebAssembly is single-threaded and has none)"],
["ASP.NET Core (MVC, minimal APIs)","<b>No</b>","Any thread-pool thread"],
["Console apps, worker services","<b>No</b>","Any thread-pool thread"]])}
<p>Library code (a NuGet package, a shared SDK for your company's GST service) doesn't know what kind of app calls it and never needs the UI thread. So it opts out of capturing the context:</p>
{C(r"""
using System.Net.Http.Json;

public class GstinClient(HttpClient http)                 // a reusable library class
{
    public async Task<GstinDetails?> LookupAsync(string gstin, CancellationToken ct = default)
    {
        using HttpResponseMessage response = await http
            .GetAsync($"gstin/{gstin}", ct)
            .ConfigureAwait(false);                       // don't hop back to the caller's context

        if (!response.IsSuccessStatusCode) return null;

        return await response.Content
            .ReadFromJsonAsync<GstinDetails>(ct)
            .ConfigureAwait(false);                       // on EVERY await in the library
    }
}

public record GstinDetails(string Gstin, string LegalName, string State);
""", "GstinClient.cs")}
{table(["Where","Use ConfigureAwait(false)?","Why"],[
["Reusable library / NuGet package","Yes, on every await","Slightly faster, and callers who (wrongly) block on your code won't deadlock"],
["UI event handlers / view models","No","You need to come back to the UI thread to update controls"],
["ASP.NET Core app code","Not needed (harmless)","There is no context to capture"],
["Console apps","Not needed","No context"]])}
{tip("<b>.NET 8</b> added <code>ConfigureAwait(ConfigureAwaitOptions)</code> on Task: e.g. <code>await task.ConfigureAwait(ConfigureAwaitOptions.SuppressThrowing)</code> waits for completion without throwing (useful when you only need \"it's finished\"). <code>ConfigureAwait(false)</code> is equivalent to <code>ConfigureAwaitOptions.None</code>.")}

<h3>4. Async all the way — never .Result or .Wait()</h3>
<p>Blocking on async code is called <b>sync-over-async</b>. With a SynchronizationContext it deadlocks; without one it wastes threads.</p>
{C(r"""
// ❌ The classic deadlock (WinForms/WPF or classic ASP.NET)
private void btnTotal_Click(object sender, EventArgs e)
{
    decimal total = GetTotalAsync().Result;   // (1) UI thread BLOCKS, waiting for the task
    lblTotal.Text = total.ToString("N2");
}

private async Task<decimal> GetTotalAsync()
{
    await Task.Delay(1000);                   // (2) captures the UI context
    return 1180m;                             // (3) continuation must run on the UI thread...
}                                             //     ...which is blocked in (1) → both wait forever. App freezes.

// ✓ Make the caller async too
private async void btnTotal_Click(object sender, EventArgs e)
{
    decimal total = await GetTotalAsync();
    lblTotal.Text = total.ToString("N2");
}
""", "Deadlock (WinForms fragment)")}
<p>In ASP.NET Core and console apps the same code won't deadlock (no context), but each blocked request holds a pool thread hostage. Under load the pool runs dry, new requests queue up, and response times explode — <b>thread-pool starvation</b>. The fix is the same everywhere: make the caller async and await.</p>
{table(["Blocking (avoid)","Async replacement"],[
["<code>task.Result</code>, <code>task.Wait()</code>","<code>await task</code>"],
["<code>task.GetAwaiter().GetResult()</code>","<code>await task</code> (GetResult still blocks; it just doesn't wrap the exception)"],
["<code>Task.WaitAll(a, b)</code>","<code>await Task.WhenAll(a, b)</code>"],
["<code>Task.WaitAny(a, b)</code>","<code>await Task.WhenAny(a, b)</code>"],
["<code>Thread.Sleep(1000)</code>","<code>await Task.Delay(1000)</code>"],
["<code>static void Main</code> calling async code","<code>static async Task Main</code> or top-level statements with await"]])}
{warn("Reading <code>.Result</code> is fine only when the task is <i>already complete</i>, for example after <code>await Task.WhenAll(...)</code> (Wednesday). Anywhere else, treat it as a bug.", "Rule")}

<h3>5. async void: only for event handlers</h3>
{C(r"""
// ❌ async void: the caller can't await it, and can't catch its exceptions
static async void SendInvoiceEmail(string to)
{
    await Task.Delay(100);
    throw new InvalidOperationException("SMTP server unavailable");
}

try
{
    SendInvoiceEmail("asha.rao@example.com");   // returns at its first await...
}
catch (Exception)
{
    Console.WriteLine("Never printed");         // ...so this try block has already finished
}
await Task.Delay(500);
// 💥 Unhandled InvalidOperationException: raised on a pool thread → the process crashes

// ✓ async Task: awaitable, and exceptions reach the caller
static async Task SendInvoiceEmailAsync(string to)
{
    await Task.Delay(100);
    throw new InvalidOperationException("SMTP server unavailable");
}

try { await SendInvoiceEmailAsync("asha.rao@example.com"); }
catch (InvalidOperationException ex) { Console.WriteLine($"Email failed: {ex.Message}"); }   // ✓ caught
""", "AsyncVoid.cs")}
<p>Watch for <i>hidden</i> async void: any async lambda passed where an <code>Action</code> is expected becomes async void.</p>
{C(r"""
List<string> customers = ["Asha", "Ravi", "Meena"];

// ❌ List.ForEach takes Action<T> → each lambda is async void; ForEach returns before any email is sent
customers.ForEach(async c => await SendInvoiceEmailAsync(c));

// ✓ Use a real loop (sequential) or Task.WhenAll (concurrent, Wednesday)
foreach (string c in customers) await SendInvoiceEmailAsync(c);
await Task.WhenAll(customers.Select(c => SendInvoiceEmailAsync(c)));
""")}

<h3>6. Writing async methods well</h3>
{C(r"""
public interface IGstRateProvider
{
    Task<decimal> GetRateAsync(string hsnCode, CancellationToken ct = default);   // accept a token (Wednesday)
}

// An implementation that happens to be synchronous: no async keyword, return a completed task
public class FixedRateProvider : IGstRateProvider
{
    public Task<decimal> GetRateAsync(string hsnCode, CancellationToken ct = default) =>
        Task.FromResult(0.18m);
}

public class InvoiceFileReader
{
    // ❌ "Eliding" async inside a using: the method returns the task immediately,
    //    the using disposes the reader, and the still-running read can fail with ObjectDisposedException
    public Task<string> ReadBad(string path)
    {
        using var reader = new StreamReader(path);
        return reader.ReadToEndAsync();
    }

    // ✓ Keep async/await whenever there's a using, a try/catch, or code that must run after
    public async Task<string> ReadAsync(string path)
    {
        using var reader = new StreamReader(path);
        return await reader.ReadToEndAsync();
    }

    // ✓ Pure pass-through with nothing around it: returning the task directly is fine
    public Task<string> ReadAllAsync(string path) => File.ReadAllTextAsync(path);
}
""", "AsyncGuidelines.cs")}
{table(["Situation","Return"],[
["Async work, no value","<code>Task</code>"],
["Async work with a value","<code>Task&lt;T&gt;</code>"],
["Hot path, usually completes synchronously","<code>ValueTask&lt;T&gt;</code>"],
["Event handler","<code>void</code> (the only valid async void)"],
["Interface requires async, implementation is sync","<code>Task.CompletedTask</code> / <code>Task.FromResult(x)</code>"],
["Sequence produced asynchronously","<code>IAsyncEnumerable&lt;T&gt;</code> (Thursday)"]])}
''',
["Calling <code>.Result</code> or <code>.Wait()</code> on a task that isn't finished.",
"Writing <code>async void</code> for anything other than an event handler, including async lambdas passed to <code>List.ForEach</code> or <code>Parallel.ForEach</code>.",
"Expecting <code>async</code> alone to run code on a background thread. It doesn't; the method runs synchronously until its first incomplete await.",
"Leaving out <code>ConfigureAwait(false)</code> in shared library code, or adding it in UI code and then touching controls from the wrong thread.",
"Returning a task from inside a <code>using</code> or <code>try</code> block without awaiting it."],
("35 min", ["Print <code>Environment.CurrentManagedThreadId</code> before and after three awaits in a console app: <code>await Task.Delay(100)</code>, <code>await Task.CompletedTask</code>, and <code>await Task.Yield()</code>. Explain which ones can change the thread and why.",
"Write <code>async void Explode()</code> and <code>async Task ExplodeAsync()</code> that both throw after an await. Call each inside try/catch and observe the difference (the first will crash the process — that's the lesson).",
"Take the Week 3 bank simulator's <code>Transfer</code> and write an <code>async Task TransferAsync</code> version that awaits a fake <code>FraudCheckAsync</code> (Task.Delay 300 ms) before debiting. Call it with await from Program.cs; then try calling it with <code>.Result</code> and explain why it doesn't deadlock in a console app."]),
[("Does marking a method async make it run on another thread?","No. It runs on the caller's thread until the first await on an incomplete task. Only the continuation may run elsewhere."),
("Why doesn't ASP.NET Core need ConfigureAwait(false) in app code?","ASP.NET Core has no SynchronizationContext, so there's nothing to capture: continuations already run on any pool thread."),
("Why can't you catch an exception from an async void method?","It returns to the caller at its first await, so the caller's try block has already completed. The exception is later raised on the SynchronizationContext or thread pool, where nobody is waiting to catch it.")],
[("Basic","What does the await keyword do?","It checks whether the awaited task is complete. If so, it continues immediately. If not, it registers the rest of the method as a continuation, returns an incomplete task to the caller and frees the thread. When the task completes, the method resumes (on the captured context if any, otherwise a pool thread), returning the result or rethrowing the original exception."),
("Basic","Why should you avoid async void?","Callers can't await it, so they don't know when it finishes, and exceptions can't be caught by the caller; they're raised on the SynchronizationContext or thread pool and typically crash the process. It's also hard to test. Use async Task; async void is only for event handlers, whose signature demands void."),
("Basic","What does \"async all the way\" mean?","Once a method is async, its callers should also be async and await it, up to the entry point (async Main, controller action, event handler). Mixing in blocking calls like .Result breaks the chain and causes deadlocks or thread starvation."),
("Intermediate","Explain the deadlock caused by calling .Result in a UI or classic ASP.NET app.","The UI thread calls .Result and blocks. Inside the async method, an await captured the UI SynchronizationContext, so its continuation must run on the UI thread. That thread is blocked waiting for the task, and the task can't finish without that thread, so both wait forever. Fix: await instead of blocking; libraries can also use ConfigureAwait(false)."),
("Intermediate","What is ConfigureAwait(false) and when should you use it?","It tells the await not to resume on the captured SynchronizationContext, letting the continuation run on any pool thread. Use it in general-purpose library code for performance and to avoid deadlocks when callers block. Don't use it in UI code that must update controls afterwards. In ASP.NET Core app code it has no effect because there is no context."),
("Intermediate","How does the compiler implement async methods?","It generates a state machine type implementing IAsyncStateMachine. Locals and parameters become fields, each await becomes a numbered state, and MoveNext runs the code up to the next incomplete await, registers itself as the continuation via an AsyncTaskMethodBuilder and returns. When the awaited task completes, MoveNext is called again and jumps to the saved state. Exceptions are caught and stored in the returned task via SetException.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Task.WhenAll, Task.WhenAny, cancellation and timeouts",
"Run independent operations at the same time, handle all of their failures, stop work cleanly with CancellationToken, and put a time limit on anything that might hang.",
[("Task.WhenAll","Returns a task that completes when <i>all</i> the given tasks complete. For Task&lt;T&gt; inputs, its result is a T[] in input order."),
("Task.WhenAny","Returns a task that completes when <i>any one</i> of the given tasks completes; its result is the winning task itself."),
("Task.WhenEach",".NET 9: an IAsyncEnumerable that yields tasks one by one in the order they complete."),
("CancellationTokenSource (CTS)","The object that <i>requests</i> cancellation: Cancel(), CancelAfter(). Owned by whoever decides to stop. Disposable."),
("CancellationToken","A read-only struct handed to the work so it can <i>observe</i> cancellation: IsCancellationRequested, ThrowIfCancellationRequested(), Register()."),
("Cooperative cancellation","Nothing is forcibly killed. The work checks the token and stops itself at a safe point."),
("OperationCanceledException","The standard exception meaning \"stopped because cancellation was requested\". A task that throws it with its token ends in the Canceled state."),
("TaskCanceledException","A subclass of OperationCanceledException thrown by Task.Delay, HttpClient and others. Catch the base type."),
("CancelAfter","Schedules the CTS to cancel itself after a time span — the standard way to implement timeouts."),
("Linked token source","CancellationTokenSource.CreateLinkedTokenSource(a, b): cancelled when any source token is cancelled. Used to combine \"caller cancelled\" with \"our timeout\"."),
("Task.WaitAsync",".NET 6: returns a task that completes when the original does, or throws TimeoutException / OperationCanceledException if the time or token runs out first."),
("CancellationToken.None","An empty token that is never cancelled; the default value for optional token parameters.")],
["Start every independent task first, <i>then</i> await them together. Awaiting one by one makes them sequential.",
"<code>await Task.WhenAll(...)</code> throws only <b>one</b> of the exceptions (don't rely on which); all of them are in the WhenAll task's <code>.Exception</code>.",
"<code>Task.WhenAny</code> never throws. Await the winner to get its result, and cancel the losers yourself.",
"Accept a <code>CancellationToken</code> as the last parameter of every async method, and pass it to everything you call.",
"Catch <code>OperationCanceledException</code>, not TaskCanceledException, so you handle both.",
"<code>WaitAsync</code> stops <i>you</i> waiting; it doesn't stop the operation. Prefer passing a token when the API accepts one."],
f'''
<h3>1. Sequential vs concurrent with Task.WhenAll</h3>
<p>A customer dashboard needs three independent pieces of data. Awaiting them one after another adds up the delays; starting all three and awaiting together costs only the slowest.</p>
{C(r"""
using System.Diagnostics;

var sw = Stopwatch.StartNew();
string name    = await GetCustomerNameAsync(7);
decimal limit  = await GetCreditLimitAsync(7);
int openOrders = await GetOpenOrderCountAsync(7);
Console.WriteLine($"Sequential: {sw.ElapsedMilliseconds} ms");    // ~1200 ms (300 + 400 + 500)

sw.Restart();
Task<string>  nameTask  = GetCustomerNameAsync(7);        // all three START here
Task<decimal> limitTask = GetCreditLimitAsync(7);
Task<int>     ordersTask = GetOpenOrderCountAsync(7);
await Task.WhenAll(nameTask, limitTask, ordersTask);      // wait for the slowest
Console.WriteLine($"Concurrent: {sw.ElapsedMilliseconds} ms");    // ~500 ms

// .Result is safe here: every task is already complete
Console.WriteLine($"{nameTask.Result}: limit ₹{limitTask.Result:N0}, {ordersTask.Result} open orders");
// Priya Sharma: limit ₹50,000, 3 open orders

static async Task<string>  GetCustomerNameAsync(int id)   { await Task.Delay(300); return "Priya Sharma"; }
static async Task<decimal> GetCreditLimitAsync(int id)    { await Task.Delay(400); return 50_000m; }
static async Task<int>     GetOpenOrderCountAsync(int id) { await Task.Delay(500); return 3; }
""", "Dashboard.cs")}
<p>When all tasks return the same type, WhenAll hands you an array <b>in the same order as the input</b>, regardless of which finished first:</p>
{C(r"""
int[] invoiceIds = [101, 102, 103, 104];
decimal[] totals = await Task.WhenAll(invoiceIds.Select(id => GetInvoiceTotalAsync(id)));
for (int i = 0; i < invoiceIds.Length; i++)
    Console.WriteLine($"INV-{invoiceIds[i]}: ₹{totals[i]:N2}");      // totals[i] belongs to invoiceIds[i]

static async Task<decimal> GetInvoiceTotalAsync(int id)
{
    await Task.Delay(Random.Shared.Next(100, 400));       // finish in random order...
    return id * 11.8m;                                     // ...results still line up with the input
}
""")}
{warn("Only run things concurrently when they're truly independent. If step 2 needs step 1's result (load the order, <i>then</i> load its customer), sequential awaits are correct. Also beware sharing one non-thread-safe object across concurrent tasks — EF Core's DbContext, for example, throws if two queries run on it at once.", "Careful")}

<h3>2. Exceptions with WhenAll</h3>
{C(r"""
string[] phones = ["9876543210", "12345", "9123456780", "999"];

Task all = Task.WhenAll(phones.Select(SendSmsAsync));
try
{
    await all;
}
catch (Exception first)
{
    Console.WriteLine($"await threw only: {first.Message}");
    foreach (Exception ex in all.Exception!.InnerExceptions)     // every failure is kept here
        Console.WriteLine($"  failed → {ex.Message}");
}

static async Task SendSmsAsync(string phone)
{
    await Task.Delay(100);
    if (phone.Length != 10) throw new ArgumentException($"Invalid mobile number {phone}");
    Console.WriteLine($"SMS sent to {phone}");
}

// SMS sent to 9876543210          (successful ones still complete; order of these two may vary)
// SMS sent to 9123456780
// await threw only: Invalid mobile number 12345     (or 999 — which one isn't guaranteed)
//   failed → Invalid mobile number 12345            (these two can also appear in either order:
//   failed → Invalid mobile number 999               both fail at ~100 ms, recorded in completion order)
""", "WhenAllExceptions.cs")}
<p>Key facts: WhenAll waits for <i>every</i> task, even after one fails (it doesn't cancel the rest). Don't rely on <i>which</i> exception <code>await</code> rethrows or on the order of <code>InnerExceptions</code>: on .NET 8 the non-generic <code>WhenAll(Task[])</code> records failures in completion order, while <code>WhenAll&lt;T&gt;</code> records them in input order. If you'd rather never throw and report per item, make each task return a result object instead — that's exactly what Saturday's downloader does.</p>
{C(r"""
// Per-item results instead of exceptions
SmsResult[] results = await Task.WhenAll(phones.Select(TrySendSmsAsync));   // never throws
Console.WriteLine($"{results.Count(r => r.Sent)} sent, {results.Count(r => !r.Sent)} failed");   // 2 sent, 2 failed

static async Task<SmsResult> TrySendSmsAsync(string phone)
{
    try { await SendSmsAsync(phone); return new SmsResult(phone, true, null); }
    catch (Exception ex) { return new SmsResult(phone, false, ex.Message); }
}

record SmsResult(string Phone, bool Sent, string? Error);   // type declarations go after top-level statements
""")}

<h3>3. Task.WhenAny: first one wins</h3>
{C(r"""
using var cts = new CancellationTokenSource();
Task<string> gatewayA = GetQuoteAsync("GatewayA", 400, cts.Token);
Task<string> gatewayB = GetQuoteAsync("GatewayB", 250, cts.Token);

Task<string> winner = await Task.WhenAny(gatewayA, gatewayB);   // completes when the FIRST one finishes
cts.Cancel();                                                    // WhenAny doesn't stop the loser; we do
Console.WriteLine($"Using {await winner}");                      // await the winner for its result (or exception)
// Using GatewayB (250 ms)

static async Task<string> GetQuoteAsync(string gateway, int ms, CancellationToken ct)
{
    await Task.Delay(ms, ct);
    return $"{gateway} ({ms} ms)";
}
""", "FastestGateway.cs")}
<h4>Handling results as they arrive</h4>
{C(r"""
List<Task<decimal>> pending = invoiceIds.Select(id => GetInvoiceTotalAsync(id)).ToList();

// .NET 9+: Task.WhenEach yields each task as it completes
await foreach (Task<decimal> done in Task.WhenEach(pending))
    Console.WriteLine($"Finished: ₹{await done:N2}");

// Before .NET 9: the WhenAny loop (O(n²) — fine for dozens of tasks, not thousands)
pending = invoiceIds.Select(id => GetInvoiceTotalAsync(id)).ToList();
while (pending.Count > 0)
{
    Task<decimal> done = await Task.WhenAny(pending);
    pending.Remove(done);
    Console.WriteLine($"Finished: ₹{await done:N2}");
}
""")}

<h3>4. CancellationToken: cooperative cancellation</h3>
<p>Two roles: the <b>CancellationTokenSource</b> is the remote control (whoever may decide to stop: a Cancel button, Ctrl+C, a timeout); the <b>CancellationToken</b> is the receiver you pass into the work. The work decides where it's safe to stop.</p>
{C(r"""
using var cts = new CancellationTokenSource();
cts.CancelAfter(TimeSpan.FromMilliseconds(700));          // auto-cancel after 700 ms

try
{
    await GenerateStatementsAsync(count: 10, cts.Token);
}
catch (OperationCanceledException)                        // also catches TaskCanceledException
{
    Console.WriteLine("Stopped: statement run cancelled");
}

static async Task GenerateStatementsAsync(int count, CancellationToken ct)
{
    for (int i = 1; i <= count; i++)
    {
        await Task.Delay(200, ct);                         // async APIs take the token and throw when cancelled
        Console.WriteLine($"Statement {i} generated");
    }
}

// Statement 1 generated
// Statement 2 generated
// Statement 3 generated
// Stopped: statement run cancelled
""", "Cancellation.cs")}
<p>CPU-bound loops don't await anything, so they must check the token themselves:</p>
{C(r"""
static decimal ReconcileLedger(IReadOnlyList<decimal> entries, CancellationToken ct)
{
    decimal balance = 0;
    for (int i = 0; i < entries.Count; i++)
    {
        if (i % 10_000 == 0)
            ct.ThrowIfCancellationRequested();     // check every 10k items: cheap, but responsive
        balance += entries[i];
    }
    return balance;
}

// Run it on the pool and let the token cancel it too (passing ct to Task.Run also prevents
// it from starting at all if cancellation was already requested)
decimal balance = await Task.Run(() => ReconcileLedger(entries, cts.Token), cts.Token);

// Register a callback that runs when cancellation is requested (e.g. abort a legacy API call)
using CancellationTokenRegistration reg = cts.Token.Register(() => Console.WriteLine("Cleanup: closing legacy connection"));
""")}
{table(["Do","Don't"],[
["Accept <code>CancellationToken ct = default</code> as the last parameter","Create a new CTS deep inside the call chain and ignore the caller's token"],
["Pass the token to every async call you make","Swallow OperationCanceledException and carry on as if nothing happened"],
["Dispose CTS objects you create (<code>using var cts</code>)","Use <code>Thread.Abort</code> (not supported in .NET Core / .NET 5+)"],
["Let OperationCanceledException propagate, and catch it at the top","Treat cancellation as an error in logs (it's a normal outcome)"]])}

<h3>5. Timeouts: CancelAfter, linked tokens and WaitAsync</h3>
<p>Most real methods have two reasons to stop: the caller cancelled (user clicked Cancel, HTTP request aborted) <i>or</i> our own time limit ran out. Link them:</p>
{C(r"""
static async Task<decimal> GetUsdInrRateAsync(CancellationToken callerToken)
{
    using var cts = CancellationTokenSource.CreateLinkedTokenSource(callerToken);
    cts.CancelAfter(TimeSpan.FromSeconds(2));                // our own limit for this call

    try
    {
        await Task.Delay(3000, cts.Token);                   // pretend: slow exchange-rate service
        return 83.20m;
    }
    catch (OperationCanceledException) when (!callerToken.IsCancellationRequested)
    {
        // The caller didn't cancel, so it must have been our timeout → report it as a timeout
        throw new TimeoutException("Exchange-rate service took longer than 2 s");
    }
}

try { decimal rate = await GetUsdInrRateAsync(CancellationToken.None); }
catch (TimeoutException ex) { Console.WriteLine(ex.Message); }
// Exchange-rate service took longer than 2 s
""", "LinkedTimeout.cs")}
<p>Some APIs don't accept a token at all. <b>.NET 6</b> added <code>WaitAsync</code> so you can at least stop <i>waiting</i>:</p>
{C(r"""
Task<string> certificate = FetchGstCertificateAsync("27AAPFU0939F1ZV");   // no CancellationToken parameter

try
{
    string pdfPath = await certificate.WaitAsync(TimeSpan.FromSeconds(5));
    Console.WriteLine($"Saved {pdfPath}");
}
catch (TimeoutException)
{
    Console.WriteLine("GST portal too slow; we'll retry later");   // the fetch itself is STILL running
}
// Overloads: WaitAsync(CancellationToken), WaitAsync(TimeSpan), WaitAsync(TimeSpan, CancellationToken)

static async Task<string> FetchGstCertificateAsync(string gstin)
{
    await Task.Delay(8000);                                         // a slow legacy call
    return $"{gstin}.pdf";
}
""", "WaitAsync.cs")}
{table(["Technique","Stops the work?","Exception on timeout","Use when"],[
["<code>cts.CancelAfter(t)</code> + pass token","Yes (cooperatively)","OperationCanceledException","The API accepts a token (most do)"],
["Linked CTS + CancelAfter","Yes","OperationCanceledException → translate to TimeoutException","Respect the caller's token <i>and</i> add your own limit"],
["<code>task.WaitAsync(t)</code> (.NET 6)","No — only stops waiting","TimeoutException","The API has no token parameter"],
["<code>WhenAny(task, Task.Delay(t))</code>","No","None — check which task won","Pre-.NET 6 code you'll still see"]])}
''',
["Awaiting independent tasks one by one and wondering why it's slow.",
"Catching the exception from <code>await Task.WhenAll</code> and assuming it was the only failure.",
"Forgetting to cancel the losing tasks after <code>Task.WhenAny</code>.",
"Accepting a CancellationToken but never passing it on (or never checking it in CPU loops).",
"Thinking <code>WaitAsync</code> or a WhenAny timeout cancels the underlying operation."],
("40 min", ["Write three fake async calls for a booking page (train availability 600 ms, fare 300 ms, seat map 450 ms). Time them sequentially and with WhenAll.",
"Send \"OTP\" SMS to 8 numbers with WhenAll where 3 are invalid. Print every failure (not just the first), then rewrite it so each task returns a result record and nothing throws.",
"Write <code>async Task&lt;string&gt; GetPnrStatusAsync(string pnr, CancellationToken ct)</code> that takes 1–4 s at random. Call it with a linked token and a 2-second limit; print \"timed out\" vs \"cancelled by user\" correctly (cancel the outer CTS from a second task after 1 s to test the second case)."]),
[("What does await Task.WhenAll throw if three tasks fail?","Only one of them — don't rely on which (on .NET 8 it depends on the overload: completion order for non-generic WhenAll, input order for WhenAll&lt;T&gt;). The WhenAll task's .Exception is an AggregateException holding all three."),
("Does Task.WhenAny cancel the other tasks?","No. They keep running. Pass them a token and cancel it once you have a winner."),
("Why is cancellation called cooperative?","The token only signals a request. The running code has to check it (or pass it to APIs that check it) and stop itself at a safe point; nothing is forcibly aborted.")],
[("Basic","What is the difference between Task.WhenAll and Task.WhenAny?","WhenAll completes when every task has completed and gives you all results (T[] in input order); if any fail, awaiting it throws one of the exceptions (which one isn't something to rely on) and the task's .Exception holds all of them. WhenAny completes as soon as one task completes and returns that task; it never throws, so you await the winner to get its result or exception."),
("Basic","How does cancellation work in .NET?","A CancellationTokenSource issues cancellation via Cancel() or CancelAfter(). Its Token is passed to the work, which checks IsCancellationRequested or calls ThrowIfCancellationRequested, or passes the token to async APIs that observe it. The work then throws OperationCanceledException, and the task ends as Canceled. It's cooperative: nothing is forcibly stopped."),
("Basic","When should you await sequentially instead of using WhenAll?","When operations depend on each other (you need the order before you can fetch its customer), when they share a non-thread-safe resource such as a DbContext, or when running everything at once would overload a downstream service (then throttle instead, Friday)."),
("Intermediate","How do you observe all exceptions from Task.WhenAll?","Keep a reference to the WhenAll task, await it in try/catch, and in the catch read whenAllTask.Exception.InnerExceptions. Alternatively make each task catch its own errors and return a result object, so WhenAll never throws and you get per-item outcomes."),
("Intermediate","How would you add a timeout to an async operation?","If it accepts a token: create a CTS (linked to the caller's token if there is one), call CancelAfter, and pass the token; translate the resulting OperationCanceledException into a TimeoutException when the caller didn't cancel. If it doesn't accept a token: use task.WaitAsync(timeout) in .NET 6+, remembering the operation keeps running in the background."),
("Intermediate","OperationCanceledException vs TaskCanceledException — which do you catch and why?","TaskCanceledException derives from OperationCanceledException and is thrown by some APIs (Task.Delay, HttpClient); others throw the base type directly (ThrowIfCancellationRequested). Catch OperationCanceledException to handle both. To tell a timeout from user cancellation, check whether the caller's token IsCancellationRequested (HttpClient timeouts also carry an inner TimeoutException since .NET 5).")])

# ================= DAY 4 =================
d4 = day(4, "THU", "HttpClient and async streams (IAsyncEnumerable)",
"Call web APIs correctly — one shared HttpClient, proper status-code handling, sensible timeouts — and produce or consume data that arrives over time with IAsyncEnumerable&lt;T&gt; and await foreach.",
[("HttpClient","The .NET class for sending HTTP requests. Thread-safe for concurrent requests and designed to be long-lived and reused."),
("SocketsHttpHandler","The default handler underneath HttpClient. It owns the connection pool; settings like PooledConnectionLifetime live here."),
("Socket exhaustion","Running out of local ports because many short-lived HttpClients leave closed connections in TIME_WAIT."),
("PooledConnectionLifetime","How long a pooled connection may be reused before being replaced, so DNS changes are eventually picked up."),
("IHttpClientFactory","A factory (Microsoft.Extensions.Http) that creates configured HttpClients and pools/rotates their handlers for you."),
("Typed client","A class that receives a configured HttpClient in its constructor and wraps one API (e.g. PinCodeClient)."),
("HttpResponseMessage","The response: StatusCode, headers and Content. Disposable."),
("EnsureSuccessStatusCode","Throws HttpRequestException if the status is not 2xx."),
("HttpRequestException","Thrown for network failures (DNS, refused connection) and by EnsureSuccessStatusCode; has a StatusCode property since .NET 5."),
("System.Net.Http.Json","Extension methods GetFromJsonAsync, PostAsJsonAsync, ReadFromJsonAsync using System.Text.Json with web defaults (camelCase, case-insensitive)."),
("HttpCompletionOption.ResponseHeadersRead","Return as soon as headers arrive, instead of buffering the whole body in memory. Use for large downloads."),
("IAsyncEnumerable&lt;T&gt;","An asynchronous sequence: each next element may require awaiting. The async version of IEnumerable&lt;T&gt;."),
("await foreach","Loops over an IAsyncEnumerable&lt;T&gt;, awaiting each element."),
("Async iterator","A method that is <code>async</code>, returns IAsyncEnumerable&lt;T&gt; and uses <code>yield return</code>."),
("[EnumeratorCancellation]","Attribute on an async iterator's CancellationToken parameter so a token passed via WithCancellation() reaches it.")],
["Create HttpClient once and reuse it (static field, singleton, or via IHttpClientFactory). Never <code>new</code> one per request.",
"Set <code>PooledConnectionLifetime</code> on a long-lived client so it notices DNS changes.",
"Always dispose the <code>HttpResponseMessage</code> (<code>using</code>), not the shared HttpClient.",
"Default <code>HttpClient.Timeout</code> is 100 seconds. A timeout surfaces as TaskCanceledException.",
"Retry only transient failures: network errors, 408, 429, 5xx. Never retry a 400 or 404.",
"IAsyncEnumerable lets the consumer start working on item 1 while item 2 is still being fetched."],
f'''
<h3>1. One shared HttpClient</h3>
{C(r"""
// ❌ A new client per call. Each disposal closes its connections, which linger in TIME_WAIT
//    for up to a few minutes. Under load you run out of sockets ("socket exhaustion").
static async Task<string> GetPageBad(string url)
{
    using var client = new HttpClient();
    return await client.GetStringAsync(url);
}

// ✓ One long-lived client for the whole app, with connections recycled every 2 minutes
//   so a changed DNS record (e.g. a failover) is eventually noticed
public static class Http
{
    public static readonly HttpClient Client = new(new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(2)
    })
    {
        Timeout = TimeSpan.FromSeconds(30)     // default is 100 s — usually far too long
    };
}
""", "SharedClient.cs")}
{warn("Configure <code>BaseAddress</code>, <code>Timeout</code> and <code>DefaultRequestHeaders</code> <i>before</i> the first request and never change them afterwards: the client is shared across threads. Per-request headers go on an <code>HttpRequestMessage</code>.", "Gotcha")}

<h3>2. Making requests and handling status codes</h3>
<p>India Post's public PIN-code API is a nice free target: <code>GET https://api.postalpincode.in/pincode/560001</code> returns a JSON array with the post offices for that PIN (it's a third-party service, so its shape and availability can change).</p>
{C(r"""
using System.Net;
using System.Net.Http.Json;

var http = new HttpClient { BaseAddress = new Uri("https://api.postalpincode.in/") };   // trailing slash matters

// 1. Simplest: GetFromJsonAsync — deserialises the body; throws HttpRequestException on non-2xx
PinCodeResponse[]? data = await http.GetFromJsonAsync<PinCodeResponse[]>("pincode/560001");
foreach (PostOffice po in data?[0].PostOffice ?? [])
    Console.WriteLine($"{po.Name}, {po.District}, {po.State}");
// e.g. Bangalore G.P.O., Bangalore, Karnataka … (live data; names may differ)

// 2. Full control: check the status yourself
using HttpResponseMessage response = await http.GetAsync("pincode/560001");
Console.WriteLine($"{(int)response.StatusCode} {response.StatusCode}");    // 200 OK

if (response.StatusCode == HttpStatusCode.NotFound)
    Console.WriteLine("No such resource");
else if (!response.IsSuccessStatusCode)
    Console.WriteLine($"Server said {(int)response.StatusCode}");
else
{
    var body = await response.Content.ReadFromJsonAsync<PinCodeResponse[]>();
    Console.WriteLine(body?[0].Message);
}

// 3. Sending JSON
// using var created = await http.PostAsJsonAsync("orders", new { Customer = "Asha Rao", Total = 2499m });
// created.EnsureSuccessStatusCode();
// var order = await created.Content.ReadFromJsonAsync<OrderDto>();

// Property names match the JSON case-insensitively (web defaults)
public record PostOffice(string Name, string District, string State, string Pincode);
public record PinCodeResponse(string Status, string Message, List<PostOffice>? PostOffice);
""", "PinCodeLookup.cs")}
{table(["Range","Meaning","Examples","Retry?"],[
["2xx","Success","200 OK, 201 Created, 204 No Content","—"],
["3xx","Redirect (HttpClient follows these automatically by default)","301, 302, 304 Not Modified","—"],
["4xx","Client error: <i>your</i> request is wrong","400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found","No — except 408 Request Timeout and 429 Too Many Requests (wait, then retry)"],
["5xx","Server error: the other side failed","500, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout","Yes, with backoff (Sunday)"]])}
{C(r"""
try
{
    var data = await http.GetFromJsonAsync<PinCodeResponse[]>("pincode/110001");
}
catch (HttpRequestException ex) when (ex.StatusCode == HttpStatusCode.TooManyRequests)
{
    Console.WriteLine("Rate limited — slow down");                // a non-2xx status (.NET 5+ sets StatusCode)
}
catch (HttpRequestException ex)
{
    Console.WriteLine($"Request failed: {ex.StatusCode?.ToString() ?? "network error"} — {ex.Message}");
}                                                                  // StatusCode is null for DNS/connection failures
catch (TaskCanceledException ex) when (ex.InnerException is TimeoutException)
{
    Console.WriteLine("HttpClient.Timeout elapsed");               // .NET 5+: timeouts carry an inner TimeoutException
}
""", "HttpErrors.cs")}

<h3>3. Timeouts and large downloads</h3>
<p><code>HttpClient.Timeout</code> applies to every request made through that client. For a specific call, use a token with <code>CancelAfter</code> (Wednesday), linked to the caller's token:</p>
{C(r"""
static async Task<string?> GetDistrictAsync(HttpClient http, string pin, CancellationToken ct)
{
    using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
    cts.CancelAfter(TimeSpan.FromSeconds(5));              // this call only: 5 s

    var data = await http.GetFromJsonAsync<PinCodeResponse[]>($"pincode/{pin}", cts.Token);
    return data?[0].PostOffice?.FirstOrDefault()?.District;
}

// Large file: don't buffer it in memory — stream it straight to disk
static async Task DownloadFileAsync(HttpClient http, string url, string path, CancellationToken ct)
{
    using HttpResponseMessage response =
        await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);   // returns once headers arrive
    response.EnsureSuccessStatusCode();

    await using Stream body = await response.Content.ReadAsStreamAsync(ct);
    await using FileStream file = File.Create(path);
    await body.CopyToAsync(file, ct);                       // copies in chunks: flat memory for a 2 GB file
}
""", "Timeouts.cs")}
{tip("With <code>ResponseHeadersRead</code>, <code>HttpClient.Timeout</code> only covers the time until headers arrive. Pass a token to <code>CopyToAsync</code> if the body download itself needs a limit.")}

<h3>4. IHttpClientFactory (preview)</h3>
<p>In ASP.NET Core you'll rarely create HttpClient yourself. The factory hands out clients whose underlying handlers are pooled and rotated (every 2 minutes by default), which solves both socket exhaustion and stale DNS, and centralises configuration (base address, headers, and later Polly retry policies in Week 43). A taste in a console app:</p>
{C(r"""
// dotnet add package Microsoft.Extensions.Http
// dotnet add package Microsoft.Extensions.DependencyInjection
using System.Net.Http.Json;
using Microsoft.Extensions.DependencyInjection;

var services = new ServiceCollection();
services.AddHttpClient<PinCodeClient>(client =>             // registers a TYPED client
{
    client.BaseAddress = new Uri("https://api.postalpincode.in/");
    client.Timeout = TimeSpan.FromSeconds(10);
});

using ServiceProvider provider = services.BuildServiceProvider();
var pins = provider.GetRequiredService<PinCodeClient>();
Console.WriteLine(await pins.GetDistrictAsync("600001"));   // e.g. Chennai

public class PinCodeClient(HttpClient http)                  // the factory injects a configured HttpClient
{
    public async Task<string?> GetDistrictAsync(string pin, CancellationToken ct = default)
    {
        var data = await http.GetFromJsonAsync<PinCodeResponse[]>($"pincode/{pin}", ct);
        return data?[0].PostOffice?.FirstOrDefault()?.District;
    }
}
""", "FactoryPreview.cs")}
{table(["Approach","Socket exhaustion?","Sees DNS changes?","Where"],[
["<code>new HttpClient()</code> per request","Yes ❌","Yes","Never"],
["One static HttpClient","No","Only with PooledConnectionLifetime","Console apps, simple tools (Saturday's project)"],
["IHttpClientFactory / typed clients","No","Yes (handler rotation)","ASP.NET Core and anything using DI"]])}

<h3>5. IAsyncEnumerable&lt;T&gt; and await foreach</h3>
<p>Last week's <code>yield return</code> produced items lazily, but each item had to be ready synchronously. An <b>async iterator</b> can await between items — perfect for paged APIs, database cursors and log tails. The consumer processes page 1 while page 2 hasn't even been requested.</p>
{C(r"""
using System.Runtime.CompilerServices;

await foreach (Order order in GetAllOrdersAsync())
{
    Console.WriteLine($"Order #{order.Id} {order.Customer} ₹{order.Amount:N0}");
    if (order.Amount >= 5000) break;                       // breaking stops further pages being fetched
}

// async + IAsyncEnumerable<T> + yield return = async iterator
static async IAsyncEnumerable<Order> GetAllOrdersAsync(
    [EnumeratorCancellation] CancellationToken ct = default)
{
    for (int page = 1; ; page++)
    {
        Order[] batch = await FetchPageAsync(page, ct);    // one "API call" per page
        if (batch.Length == 0) yield break;
        foreach (Order order in batch)
            yield return order;                            // hand over items while later pages aren't fetched yet
    }
}

static async Task<Order[]> FetchPageAsync(int page, CancellationToken ct)
{
    await Task.Delay(300, ct);
    Console.WriteLine($"  [fetched page {page}]");
    if (page > 3) return Array.Empty<Order>();
    return Enumerable.Range((page - 1) * 2 + 1, 2)
                     .Select(i => new Order(i, $"Customer {i}", 1000m * i))
                     .ToArray();
}

record Order(int Id, string Customer, decimal Amount);

//   [fetched page 1]
// Order #1 Customer 1 ₹1,000
// Order #2 Customer 2 ₹2,000
//   [fetched page 2]
// Order #3 Customer 3 ₹3,000
// Order #4 Customer 4 ₹4,000
//   [fetched page 3]
// Order #5 Customer 5 ₹5,000
""", "AsyncStreams.cs")}
{C(r"""
// Passing a token to an async stream you didn't create: WithCancellation
using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(1));
try
{
    await foreach (Order o in GetAllOrdersAsync().WithCancellation(cts.Token))   // flows into [EnumeratorCancellation]
        Console.WriteLine(o.Id);
}
catch (OperationCanceledException) { Console.WriteLine("Stopped after 1 s"); }
""")}

<h3>6. Where you'll meet async streams</h3>
{C(r"""
using System.Net.Http.Json;                       // GetFromJsonAsAsyncEnumerable

// .NET 7+: read a big file line by line without blocking
await foreach (string line in File.ReadLinesAsync("payments.csv"))
    if (line.Contains("FAILED")) Console.WriteLine(line);

// .NET 8+: stream a JSON array from an API, item by item, without loading it all
await foreach (Payment? p in http.GetFromJsonAsAsyncEnumerable<Payment>("payments/today"))
    Console.WriteLine($"{p?.Id}: ₹{p?.Amount:N2}");

// .NET 6+: the same for any stream
// await foreach (var p in JsonSerializer.DeserializeAsyncEnumerable<Payment>(stream)) { ... }

// EF Core (Week 14+): await foreach (var c in db.Customers.AsAsyncEnumerable()) { ... }
// ASP.NET Core: an endpoint can return IAsyncEnumerable<T> and the JSON is streamed as it's produced

record Payment(string Id, decimal Amount);
""", "AsyncStreamSources.cs")}
{table(["","Task&lt;List&lt;T&gt;&gt;","IAsyncEnumerable&lt;T&gt;"],[
["First item available","After everything is loaded","As soon as it's ready"],
["Memory","All items at once","One item / page at a time"],
["Can stop early and save work","No (already fetched)","Yes (break stops fetching)"],
["Can count / index / reuse","Yes","No — enumerate again to re-run"],
["Best for","Small results you need as a whole","Large, paged or unbounded data"]])}
''',
["<code>using var client = new HttpClient()</code> inside a method that's called per request.",
"Forgetting to dispose <code>HttpResponseMessage</code>, holding connections longer than needed.",
"Calling <code>.Content.ReadAsStringAsync()</code> on a 2 GB response instead of streaming it.",
"Retrying 4xx errors like 400 or 404, which will fail the same way every time.",
"Forgetting <code>[EnumeratorCancellation]</code>, so a token passed with WithCancellation never reaches the iterator."],
("40 min", ["Write a <code>PinCodeClient</code> with a shared HttpClient and <code>Task&lt;string?&gt; GetStateAsync(string pin, CancellationToken ct)</code>. Look up 5 PIN codes concurrently with WhenAll. (No internet? Point it at a fake <code>HttpMessageHandler</code> that returns canned JSON — great practice for Week 10's testing.)",
"Handle 404, 429, 500, timeouts and DNS failures with distinct messages. Test the timeout with a 1 ms per-request limit and the DNS failure with <code>https://no-such-host.invalid/</code>.",
"Write <code>async IAsyncEnumerable&lt;string&gt; TailAsync(string path, [EnumeratorCancellation] CancellationToken ct)</code> that yields new lines appended to a log file (poll every 500 ms). Consume it with await foreach and stop it after 10 s with WithCancellation."]),
[("Why is a static HttpClient better than a new one per call, and what's its one weakness?","It reuses pooled connections, avoiding socket exhaustion and connection setup cost. Its weakness is that it may keep using old connections after a DNS change; set PooledConnectionLifetime to fix that."),
("What does EnsureSuccessStatusCode do?","Throws HttpRequestException (with StatusCode set) if the response status isn't in the 2xx range; otherwise does nothing."),
("What's the difference between IEnumerable&lt;T&gt; with yield and IAsyncEnumerable&lt;T&gt;?","Both are lazy, but an async iterator can await between items (network, disk) without blocking a thread, and is consumed with await foreach.")],
[("Basic","Why shouldn't you create a new HttpClient for every request?","Each disposed client closes its connections, which remain in TIME_WAIT on the OS for a while. Under load you exhaust available sockets and requests start failing; you also pay TCP/TLS setup every time. Reuse a single client (or use IHttpClientFactory), which pools connections and is safe for concurrent requests."),
("Basic","What does HttpClient do when a request returns 404?","GetAsync/SendAsync return normally with StatusCode = NotFound; no exception. GetStringAsync and GetFromJsonAsync, or calling EnsureSuccessStatusCode, throw HttpRequestException with StatusCode 404. Network failures (DNS, refused connection) always throw HttpRequestException with a null StatusCode."),
("Basic","What is IAsyncEnumerable&lt;T&gt; and when would you use it?","An asynchronous sequence consumed with await foreach, where getting each item may involve awaiting. Use it for paged APIs, streaming database results, reading large files or real-time feeds, so consumers can process items as they arrive with low memory instead of waiting for a whole list."),
("Intermediate","What problems does IHttpClientFactory solve?","It pools HttpMessageHandlers and rotates them periodically, avoiding both socket exhaustion (from creating many clients) and stale DNS (from one client living forever). It also centralises configuration as named or typed clients and integrates with DI, logging and resilience handlers like Polly."),
("Intermediate","How do you implement per-request timeouts with HttpClient and tell them apart from cancellation?","Create a CTS linked to the caller's token, call CancelAfter(timeout), and pass its token to the request. If OperationCanceledException is thrown and the caller's token is not cancelled, it was the timeout. For HttpClient.Timeout itself, .NET 5+ throws TaskCanceledException with an inner TimeoutException."),
("Intermediate","How do you pass a CancellationToken into an async iterator?","Add a CancellationToken parameter marked [EnumeratorCancellation]. Callers can pass it directly as an argument, or use source.WithCancellation(token) in await foreach; the attribute makes the compiler combine that token with the parameter. Pass the token to every await inside the iterator.")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Thread safety, concurrent collections and Parallel",
"See a race condition happen, fix it with lock, Interlocked or a concurrent collection, throttle async work with SemaphoreSlim, use Parallel.For/ForEach/ForEachAsync for the right kind of work, and recognise and prevent deadlocks.",
[("Shared state","Data that more than one thread can read and write at the same time, e.g. a field, a static, or a captured local."),
("Race condition","A bug where the result depends on the unpredictable timing of threads, e.g. two increments overlapping so one is lost."),
("Atomic operation","An operation that happens completely or not at all, with no other thread able to see it half-done."),
("Critical section","A block of code that only one thread may execute at a time."),
("lock / Monitor","C#'s lock statement: Monitor.Enter/Exit in a try/finally on a private object. Mutual exclusion for synchronous code."),
("System.Threading.Lock",".NET 9 + C# 13: a dedicated lock type. lock(_lock) on it uses Lock.EnterScope(), which is faster and clearer than locking an object."),
("Interlocked","Static methods (Increment, Add, Exchange, CompareExchange) that perform single updates atomically using CPU instructions, without a lock."),
("ConcurrentDictionary&lt;K,V&gt;","A thread-safe dictionary with atomic helpers like GetOrAdd, AddOrUpdate, TryRemove."),
("ConcurrentQueue&lt;T&gt;","A thread-safe FIFO queue (Enqueue, TryDequeue) — lock-free for producers and consumers."),
("SemaphoreSlim","Allows up to N callers into a section at once. WaitAsync makes it the standard tool for async throttling and async locks."),
("Parallel.For / ForEach","Run a loop body on multiple threads for CPU-bound work, blocking until all iterations finish."),
("Parallel.ForEachAsync",".NET 6: run an async body for each item with a cap on how many run at once (MaxDegreeOfParallelism)."),
("Deadlock","Two or more threads each waiting for something another holds, so none can ever proceed."),
("Thread-safe","Behaves correctly when called from multiple threads at once, without extra synchronisation by the caller.")],
["<code>count++</code> is three steps (read, add, write). Two threads can interleave them and lose updates.",
"The best shared state is no shared state: give each task its own data, then combine results at the end.",
"lock on a <b>private readonly</b> object (or a .NET 9 <code>Lock</code>), never on <code>this</code>, a type, or a string.",
"You can't <code>await</code> inside a lock. Use <code>SemaphoreSlim(1, 1)</code> with WaitAsync for async code.",
"Concurrent collections make <i>each call</i> atomic, not a sequence of calls. Use their combined methods (GetOrAdd, AddOrUpdate).",
"<code>Parallel.ForEach</code> with an async lambda is async void. Use <code>Parallel.ForEachAsync</code>."],
f'''
<h3>1. A race condition, live — and lock</h3>
{C(r"""
int counter = 0;
Parallel.For(0, 1_000_000, _ => counter++);    // many threads doing read → add → write
Console.WriteLine(counter);                    // e.g. 431,207 on a multi-core PC — different every run, rarely 1,000,000
""", "RaceDemo.cs")}
{table(["Time","Thread A","Thread B","counter in memory"],[
["1","reads 41","","41"],
["2","","reads 41","41"],
["3","writes 42","","42"],
["4","","writes 42","42 ← one increment lost"]])}
<p>The classic real-world version is <b>check-then-act</b>: two threads both see enough balance, and both withdraw. A <code>lock</code> makes the check and the update one indivisible step:</p>
{C(r"""
var wallet = new Wallet(openingBalance: 1_000m);
int paid = 0;

Parallel.For(0, 100, _ =>                      // 100 simultaneous ₹50 UPI payments
{
    if (wallet.TryPay(50m)) Interlocked.Increment(ref paid);
});
Console.WriteLine($"{paid} payments, balance ₹{wallet.Balance}");   // 20 payments, balance ₹0 — every time

public class Wallet(decimal openingBalance)
{
    private readonly object _sync = new();     // private: no outside code can lock on it
    private decimal _balance = openingBalance;

    public decimal Balance { get { lock (_sync) return _balance; } }

    public bool TryPay(decimal amount)
    {
        lock (_sync)                           // one thread at a time in here
        {
            if (_balance < amount) return false;   // check...
            _balance -= amount;                    // ...and act, as one atomic unit
            return true;
        }
    }
}
""", "Wallet.cs")}
<p><b>.NET 9</b> (with C# 13) adds a purpose-built lock type. The syntax stays the same; the compiler sees the type and generates faster code:</p>
{C(r"""
public class WalletNet9(decimal openingBalance)
{
    private readonly Lock _sync = new();       // System.Threading.Lock (.NET 9+)
    private decimal _balance = openingBalance;

    public bool TryPay(decimal amount)
    {
        lock (_sync)                           // compiles to: using (_sync.EnterScope()) { ... }
        {
            if (_balance < amount) return false;
            _balance -= amount;
            return true;
        }
    }
}
""", "WalletNet9.cs")}
{warn("<code>await</code> inside a <code>lock</code> is a compile error (CS1996): a lock is owned by a thread, and after an await you may be on a different thread. Use SemaphoreSlim (section 4) for async critical sections.", "Rule")}

<h3>2. Interlocked: lock-free single updates</h3>
{C(r"""
decimal[] payments = [1180m, 499.50m, 2360m, 99m, 15_000m];

int processed = 0;
long totalPaise = 0;                              // Interlocked has no decimal overloads → count in paise

Parallel.ForEach(payments, amount =>
{
    Interlocked.Increment(ref processed);
    Interlocked.Add(ref totalPaise, (long)(amount * 100));
});
Console.WriteLine($"{processed} payments, ₹{totalPaise / 100m:N2}");   // 5 payments, ₹19,138.50

// Exchange: swap in a new value and get the old one back atomically
int batchNumber = 7;
int previous = Interlocked.Exchange(ref batchNumber, 8);              // previous = 7

// CompareExchange: "set it only if it's still what I expect" — first writer wins
int winnerId = 0;
Parallel.For(1, 9, workerId => Interlocked.CompareExchange(ref winnerId, workerId, 0));
Console.WriteLine($"Winner: worker {winnerId}");    // exactly one worker id, never overwritten
""", "InterlockedDemo.cs")}
{table(["Need","Use"],[
["Increment/decrement/add to one int or long","<code>Interlocked</code>"],
["Several fields that must change together, or check-then-act","<code>lock</code> (or .NET 9 <code>Lock</code>)"],
["A critical section containing <code>await</code>","<code>SemaphoreSlim(1, 1)</code>"],
["A shared dictionary / queue","<code>ConcurrentDictionary</code> / <code>ConcurrentQueue</code>"],
["Data that never changes after creation","Nothing! Immutable and frozen collections (Week 4) are safe to read from any thread"]])}

<h3>3. Concurrent collections</h3>
{C(r"""
using System.Collections.Concurrent;

string[] orderCities = ["Pune", "Delhi", "pune", "Chennai", "Delhi", "Pune", "Kochi"];

// ❌ Dictionary<string,int> here would corrupt itself or throw under concurrent writes
var ordersByCity = new ConcurrentDictionary<string, int>(StringComparer.OrdinalIgnoreCase);

Parallel.ForEach(orderCities, city =>
    ordersByCity.AddOrUpdate(city, addValue: 1, updateValueFactory: (_, current) => current + 1));

foreach (var (city, count) in ordersByCity.OrderByDescending(kv => kv.Value))
    Console.WriteLine($"{city}: {count}");
// Pune: 3   (key spelling is whichever thread added it first)
// Delhi: 2
// Chennai: 1   (equal counts can come out in either order)
// Kochi: 1

// GetOrAdd: atomic "find or create". Under contention the factory MAY run more than once
// (only one result is kept), so the factory must be cheap and side-effect free…
var gstRates = new ConcurrentDictionary<string, decimal>();
decimal rate = gstRates.GetOrAdd("8471", hsn => hsn.StartsWith("84") ? 0.18m : 0.12m);

// …or wrap expensive work in Lazy<T> so it's created only once
var reports = new ConcurrentDictionary<int, Lazy<string>>();
string report = reports.GetOrAdd(2026, year => new Lazy<string>(() => $"Annual report {year}")).Value;

// ConcurrentQueue: many producers, many consumers, no locks
var printQueue = new ConcurrentQueue<string>();
Parallel.For(1, 6, i => printQueue.Enqueue($"INV-{i:000}"));
while (printQueue.TryDequeue(out string? invoice))
    Console.WriteLine($"Printing {invoice}");          // order depends on which thread enqueued first
""", "ConcurrentCollections.cs")}
{warn("Each method is atomic, but two calls in a row are not: <code>if (!dict.ContainsKey(k)) dict[k] = v;</code> is still a race. Use <code>TryAdd</code>, <code>GetOrAdd</code> or <code>AddOrUpdate</code>, which do it in one step.", "Gotcha")}
<p>Others worth knowing: <code>ConcurrentBag&lt;T&gt;</code> (unordered), <code>BlockingCollection&lt;T&gt;</code> (bounded producer/consumer with blocking), and <code>System.Threading.Channels</code> — the modern async producer/consumer queue you'll use with background services later.</p>

<h3>4. SemaphoreSlim: async throttling and async locks</h3>
<p>Starting 500 HTTP calls at once with WhenAll may get you rate-limited (429) or overload a partner API. A semaphore with N slots lets at most N callers in at a time; the rest <i>asynchronously</i> wait their turn.</p>
{C(r"""
var gate = new SemaphoreSlim(initialCount: 3, maxCount: 3);   // the e-invoice portal allows 3 parallel calls
int inFlight = 0;

await Task.WhenAll(Enumerable.Range(1, 10).Select(SubmitInvoiceAsync));
Console.WriteLine("All submitted");

async Task SubmitInvoiceAsync(int invoiceNo)
{
    await gate.WaitAsync();                  // take a slot, or wait (no thread blocked) until one frees up
    try
    {
        int now = Interlocked.Increment(ref inFlight);
        Console.WriteLine($"Submitting INV-{invoiceNo:000} (in flight: {now})");
        await Task.Delay(500);               // pretend: HTTP POST to the portal
    }
    finally
    {
        Interlocked.Decrement(ref inFlight);
        gate.Release();                      // ALWAYS in finally, or a failure leaks a slot forever
    }
}

// "in flight" never exceeds 3; 10 invoices take ~2 s (4 waves × 500 ms) instead of 0.5 s unthrottled
// or 5 s sequential
""", "Throttling.cs")}
{C(r"""
// SemaphoreSlim(1, 1) = an async-compatible lock
public class TokenCache(HttpClient http)
{
    private readonly SemaphoreSlim _mutex = new(1, 1);
    private string? _token;
    private DateTime _expiresUtc;

    public async Task<string> GetTokenAsync(CancellationToken ct = default)
    {
        await _mutex.WaitAsync(ct);          // only one caller refreshes the token at a time
        try
        {
            if (_token is null || DateTime.UtcNow >= _expiresUtc)
            {
                _token = await http.GetStringAsync("auth/token", ct);   // ✓ await inside is fine
                _expiresUtc = DateTime.UtcNow.AddMinutes(55);
            }
            return _token;
        }
        finally { _mutex.Release(); }
    }
}
""", "TokenCache.cs")}

<h3>5. Parallel.For, Parallel.ForEach and Parallel.ForEachAsync</h3>
{C(r"""
// CPU-bound: compute GST on 1 million invoice lines using all cores
decimal[] amounts = Enumerable.Range(1, 1_000_000).Select(i => (decimal)(i % 9000 + 100)).ToArray();
decimal[] gst = new decimal[amounts.Length];

Parallel.For(0, amounts.Length, i =>
{
    gst[i] = Math.Round(amounts[i] * 0.18m, 2);    // each index written by exactly one thread → no lock
});

// Limit how many cores it may use and allow cancellation
using var cts = new CancellationTokenSource();
var options = new ParallelOptions
{
    MaxDegreeOfParallelism = Math.Max(1, Environment.ProcessorCount / 2),
    CancellationToken = cts.Token
};
Parallel.ForEach(Directory.EnumerateFiles(".", "*.csv"), options, file =>
{
    int lines = File.ReadLines(file).Count();      // fine for a demo; heavy parsing would go here
    Console.WriteLine($"{Path.GetFileName(file)}: {lines} lines");
});

// I/O-bound with a concurrency cap (.NET 6+): the async-aware version
string[] gstins = ["27AAPFU0939F1ZV", "29AAGCB7383J1Z4", "07AAACI1195H1ZK", "33AABCT1332L1ZZ"];
var ioOptions = new ParallelOptions { MaxDegreeOfParallelism = 2, CancellationToken = cts.Token };

await Parallel.ForEachAsync(gstins, ioOptions, async (gstin, ct) =>
{
    await Task.Delay(400, ct);                     // pretend: verify GSTIN with the portal
    Console.WriteLine($"{gstin}: Active");
});
""", "ParallelDemo.cs")}
{warn("<code>Parallel.ForEach(items, async item =&gt; await SaveAsync(item))</code> compiles, but the lambda becomes <code>async void</code>: ForEach returns as soon as each body hits its first await, nothing waits for the saves, and exceptions crash the process. Use <code>Parallel.ForEachAsync</code> or SemaphoreSlim + WhenAll.", "Trap")}
{table(["","Parallel.For / ForEach","Parallel.ForEachAsync (.NET 6)","SemaphoreSlim + Task.WhenAll"],[
["Work type","CPU-bound","I/O-bound (async body)","I/O-bound (async body)"],
["Blocks the caller?","Yes, until all iterations finish","No, returns a Task","No, returns a Task"],
["Concurrency limit","MaxDegreeOfParallelism (default: no fixed limit)","MaxDegreeOfParallelism (default: processor count)","Semaphore count"],
["Results","Write to an array by index or use thread-safe collections","Same","WhenAll gives a T[] in order"],
["On first exception","Stops starting new iterations, throws AggregateException","Stops starting new items, throws the exception","Others keep running; await throws one of the exceptions"]])}

<h3>6. Deadlocks</h3>
<p>A deadlock needs threads holding one resource while waiting for another, in a cycle. Bank transfers locking two accounts are the textbook case:</p>
{C(r"""
var sb1001 = new Account("SB1001", 5_000m);
var sb1002 = new Account("SB1002", 5_000m);

// ❌ Locks taken in "from, to" order: two opposite transfers can deadlock
static void Transfer(Account from, Account to, decimal amount)
{
    lock (from.Sync)
    {
        Thread.Sleep(10);                  // widen the window so it happens reliably in the demo
        lock (to.Sync)
        {
            from.Balance -= amount;
            to.Balance += amount;
        }
    }
}
// Task t1 = Task.Run(() => Transfer(sb1001, sb1002, 100));   // holds SB1001, waits for SB1002
// Task t2 = Task.Run(() => Transfer(sb1002, sb1001, 200));   // holds SB1002, waits for SB1001
// await Task.WhenAll(t1, t2);                                  // never completes

// ✓ Always lock in a global order (here: by account number), whatever the direction
static void SafeTransfer(Account from, Account to, decimal amount)
{
    var (first, second) = string.CompareOrdinal(from.Number, to.Number) < 0 ? (from, to) : (to, from);
    lock (first.Sync)
    lock (second.Sync)
    {
        from.Balance -= amount;
        to.Balance += amount;
    }
}

await Task.WhenAll(
    Task.Run(() => SafeTransfer(sb1001, sb1002, 100)),
    Task.Run(() => SafeTransfer(sb1002, sb1001, 200)));
Console.WriteLine($"{sb1001.Balance} {sb1002.Balance}");   // 5100 4900

public class Account(string number, decimal balance)
{
    public string Number { get; } = number;
    public decimal Balance { get; set; } = balance;
    public object Sync { get; } = new();
}
""", "Deadlock.cs")}
{table(["Prevention","How"],[
["Lock ordering","Always acquire multiple locks in the same global order"],
["Hold locks briefly","No I/O, no calls into unknown code (events, callbacks) while holding a lock"],
["Timeouts","<code>Monitor.TryEnter(obj, timeout)</code> or <code>await semaphore.WaitAsync(timeout)</code>, then back off"],
["Fewer locks","One coarse lock, or no shared state at all (immutable data, message passing with Channels)"],
["No sync-over-async","Tuesday's .Result deadlock is the async flavour of the same problem"]])}
''',
["Locking on <code>this</code>, <code>typeof(X)</code> or a string literal, which outside code can also lock.",
"Protecting writes with a lock but reading the same fields without it.",
"Using a check-then-act sequence on a ConcurrentDictionary instead of GetOrAdd/AddOrUpdate.",
"Forgetting <code>Release()</code> in a <code>finally</code>, slowly leaking semaphore slots until everything hangs.",
"Passing an async lambda to <code>Parallel.ForEach</code> or using Parallel.For for I/O-bound work."],
("40 min", ["Reproduce the lost-update race with a <code>Dictionary&lt;string,int&gt;</code> word count over 10 text files read in parallel. Fix it three ways: lock, ConcurrentDictionary.AddOrUpdate, and per-file dictionaries merged at the end. Time each.",
"Make the Week 3 bank account thread-safe: 50 tasks deposit ₹100 and 50 withdraw ₹100 at once; the final balance must equal the opening balance every run.",
"Call a fake <code>CheckStockAsync(sku)</code> (random 200–600 ms) for 30 SKUs with at most 5 in flight, first with SemaphoreSlim + WhenAll, then with Parallel.ForEachAsync. Print the max in-flight count you observed."]),
[("Why can't you await inside a lock statement?","A Monitor lock is owned by a thread and must be released by that thread; after an await the method may resume on a different thread. The compiler forbids it (CS1996). Use SemaphoreSlim.WaitAsync instead."),
("Is ConcurrentDictionary.GetOrAdd's factory guaranteed to run once?","No. Under contention several threads may run it; only one value is stored and returned to everyone. Use Lazy&lt;T&gt; values if the factory must run once."),
("Which Parallel API for 200 HTTP calls with at most 8 at once?","Parallel.ForEachAsync with MaxDegreeOfParallelism = 8, or SemaphoreSlim(8) + Task.WhenAll. Not Parallel.ForEach.")],
[("Basic","What is a race condition? Give an example.","A bug where correctness depends on thread timing. Example: two threads run balance -= amount after both checked the balance was sufficient; or two threads run counter++ and one increment is lost because read-modify-write steps interleave. Fix by making the operation atomic (lock, Interlocked) or by not sharing the state."),
("Basic","What is the difference between lock and Interlocked?","lock gives mutual exclusion over any block of code, so it can protect several fields and check-then-act logic, at the cost of possible contention. Interlocked performs a single operation (increment, add, exchange, compare-exchange) atomically on one variable using CPU instructions, without blocking; it can't protect multi-step logic."),
("Basic","How do you limit the number of concurrent async operations?","Use SemaphoreSlim(n): await WaitAsync() before each operation and Release() in a finally, combined with Task.WhenAll. Or use Parallel.ForEachAsync with ParallelOptions.MaxDegreeOfParallelism = n (.NET 6+)."),
("Intermediate","What does the System.Threading.Lock type in .NET 9 change?","It's a dedicated lock object. When a lock statement targets a Lock (with C# 13), the compiler calls Lock.EnterScope() and disposes the scope instead of using Monitor on an arbitrary object, which is faster and makes intent explicit. The same rules apply: keep sections short and never await inside."),
("Intermediate","Compare Parallel.ForEach, Parallel.ForEachAsync and Task.WhenAll.","Parallel.ForEach is for CPU-bound synchronous bodies and blocks the caller until done. Parallel.ForEachAsync runs async bodies with a degree-of-parallelism cap and returns a Task, ideal for throttled I/O. Task.WhenAll awaits tasks you've already started; it has no built-in limit, so pair it with SemaphoreSlim for large batches."),
("Intermediate","What is a deadlock and how do you prevent it?","Two or more threads each hold a resource and wait for one held by another, forming a cycle, so none can continue. Prevent it with a global lock order, holding locks briefly without calling external code, using timeouts (Monitor.TryEnter, WaitAsync(timeout)), reducing shared state, and avoiding sync-over-async blocking such as .Result on a context-bound task.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Micro-project 6: Async web-page downloader",
"Build a console tool that reads URLs from a file, downloads them concurrently with a configurable limit (SemaphoreSlim and Parallel.ForEachAsync), saves each page to disk, and reports time, bytes, successes and failures — then compare it with a plain sequential loop. Budget: about 4 hours.",
[("Throughput","How much work finishes per unit of time, e.g. pages per second."),
("Latency","How long one operation takes from start to finish, e.g. 800 ms for one page."),
("Max concurrency","The most operations allowed in flight at once; protects both your machine and the servers you call."),
("Speed-up","Sequential time ÷ concurrent time. For I/O-bound work it's limited by the slowest item and the concurrency cap, not by CPU cores."),
("Test double","A stand-in implementation (here, <code>FakePageSource</code>) that behaves like the real dependency without needing the network.")],
["Downloads are I/O-bound: concurrency helps hugely even on one core.",
"All network access goes through an <code>IPageSource</code> interface, so an offline fake can replace HTTP (useful when the sandbox or your office Wi-Fi blocks sites).",
"Each download returns a <code>DownloadResult</code> instead of throwing, so one bad URL never stops the batch.",
"Two concurrent strategies side by side: SemaphoreSlim + Task.WhenAll, and Parallel.ForEachAsync.",
"Tomorrow adds Ctrl+C cancellation, per-request timeouts, retries with backoff and live progress."],
f'''
<h3>Requirements</h3>
<ul>
<li>Read URLs from a text file (default <code>urls.txt</code>): one per line, ignore blank lines and <code>#</code> comments, reject anything that isn't an absolute http/https URL, and skip duplicates — reporting each rejected line.</li>
<li>Download every URL and save the body to <code>downloads/&lt;mode&gt;/&lt;safe-file-name&gt;.html</code>.</li>
<li>Run three ways and time each: <b>sequential</b>, <b>SemaphoreSlim + Task.WhenAll</b>, and <b>Parallel.ForEachAsync</b>, both concurrent modes capped at <code>--max N</code> (default 4).</li>
<li>For every URL report OK/FAIL, elapsed ms, bytes or the error (HTTP status, DNS failure…). Print totals and the speed-up.</li>
<li>Non-2xx responses and network errors are failures, not crashes.</li>
<li><code>--offline</code> uses a fake page source with random latency, so everything works without internet.</li>
<li>One shared, correctly configured <code>HttpClient</code> (Thursday).</li>
</ul>

<h3>Scaffold</h3>
{C(r"""
mkdir Downloader && cd Downloader
dotnet new sln -n Downloader
dotnet new classlib -n Downloader.Core
dotnet new console  -n Downloader.App
dotnet sln add Downloader.Core Downloader.App
dotnet add Downloader.App reference Downloader.Core
rm Downloader.Core/Class1.cs
""", lang="bash")}
{C(r"""
Downloader/
├─ Downloader.sln
├─ Downloader.Core/
│  ├─ DownloadResult.cs      (DownloadStatus, DownloadResult, DownloadSummary)
│  ├─ DownloadOptions.cs
│  ├─ IPageSource.cs         (IPageSource, PageContent)
│  ├─ HttpPageSource.cs
│  ├─ FakePageSource.cs
│  ├─ FileNames.cs
│  ├─ UrlList.cs
│  └─ PageDownloader.cs
└─ Downloader.App/
   ├─ Program.cs
   └─ urls.txt               (copied to the output folder)
""", lang="text")}

<h3>Step 1 — Results and options</h3>
{C(r"""
namespace Downloader.Core;

public enum DownloadStatus { Succeeded, Failed, Cancelled }

public sealed record DownloadResult(
    Uri Url,
    DownloadStatus Status,
    TimeSpan Elapsed,
    int? StatusCode = null,
    long Bytes = 0,
    string? FilePath = null,
    string? Error = null,
    int Attempts = 1)
{
    public bool Success => Status == DownloadStatus.Succeeded;

    public static DownloadResult Cancelled(Uri url, TimeSpan elapsed = default, int attempts = 0) =>
        new(url, DownloadStatus.Cancelled, elapsed, Error: "cancelled", Attempts: attempts);
}

public sealed record DownloadSummary(IReadOnlyList<DownloadResult> Results, TimeSpan Total)
{
    public int Succeeded => Results.Count(r => r.Status == DownloadStatus.Succeeded);
    public int Failed    => Results.Count(r => r.Status == DownloadStatus.Failed);
    public int Cancelled => Results.Count(r => r.Status == DownloadStatus.Cancelled);
    public long TotalBytes => Results.Sum(r => r.Bytes);
}
""", "Downloader.Core/DownloadResult.cs")}
{C(r"""
namespace Downloader.Core;

public sealed record DownloadOptions
{
    public int MaxConcurrency { get; init; } = 4;
    public string OutputDirectory { get; init; } = "downloads";
}
""", "Downloader.Core/DownloadOptions.cs")}

<h3>Step 2 — The page source abstraction</h3>
<p>The downloader only needs \"give me the status code and bytes for this URL\". Hiding HTTP behind an interface lets us swap in a fake for offline runs today and for unit tests in Week 10.</p>
{C(r"""
namespace Downloader.Core;

public sealed record PageContent(int StatusCode, byte[] Body);

public interface IPageSource
{
    /// <summary>Fetches a page. Returns non-2xx statuses normally; throws for network failures.</summary>
    Task<PageContent> GetAsync(Uri url, CancellationToken ct);
}
""", "Downloader.Core/IPageSource.cs")}
{C(r"""
namespace Downloader.Core;

public sealed class HttpPageSource(HttpClient http) : IPageSource
{
    public async Task<PageContent> GetAsync(Uri url, CancellationToken ct)
    {
        using HttpResponseMessage response = await http.GetAsync(url, ct);
        byte[] body = await response.Content.ReadAsByteArrayAsync(ct);   // web pages are small: buffering is fine
        return new PageContent((int)response.StatusCode, body);
    }
}
""", "Downloader.Core/HttpPageSource.cs")}
{C(r"""
using System.Text;

namespace Downloader.Core;

/// <summary>
/// Simulates a web server so the project runs without internet.
/// Hosts ending in .invalid fail like a DNS error; /status/NNN returns that status;
/// /delay/N waits N extra seconds (same conventions as httpbin.org).
/// </summary>
public sealed class FakePageSource(int minDelayMs = 200, int maxDelayMs = 1200, double transientFailureRate = 0)
    : IPageSource
{
    public async Task<PageContent> GetAsync(Uri url, CancellationToken ct)
    {
        int delay = Random.Shared.Next(minDelayMs, maxDelayMs + 1);
        await Task.Delay(delay, ct);                                   // "network latency"; honours cancellation

        if (url.Host.EndsWith(".invalid", StringComparison.OrdinalIgnoreCase))
            throw new HttpRequestException($"Name or service not known ({url.Host}:{url.Port})");

        string path = url.AbsolutePath;
        if (path.StartsWith("/status/") && int.TryParse(path["/status/".Length..], out int code))
            return new PageContent(code, []);
        if (path.StartsWith("/delay/") && int.TryParse(path["/delay/".Length..], out int seconds))
            await Task.Delay(TimeSpan.FromSeconds(seconds), ct);

        if (Random.Shared.NextDouble() < transientFailureRate)
            return new PageContent(503, []);                           // Service Unavailable: worth retrying (Sunday)

        string html = $"<!doctype html><title>{url.Host}</title><h1>{url}</h1>" +
                      $"<p>Fake page served in {delay} ms.</p>" + new string(' ', delay * 10);
        return new PageContent(200, Encoding.UTF8.GetBytes(html));
    }
}
""", "Downloader.Core/FakePageSource.cs")}

<h3>Step 3 — Safe file names and the URL file</h3>
{C(r"""
using System.Security.Cryptography;
using System.Text;

namespace Downloader.Core;

public static class FileNames
{
    private static readonly char[] Invalid = Path.GetInvalidFileNameChars();

    // https://learn.microsoft.com/en-us/dotnet/  →  learn.microsoft.com_en-us_dotnet.html
    public static string FromUrl(Uri url)
    {
        string path = url.AbsolutePath.Trim('/');
        string raw = path.Length == 0 ? url.Host : $"{url.Host}_{path}";

        var sb = new StringBuilder(raw.Length);
        foreach (char c in raw)
            sb.Append(c is '/' or '\\' or ':' || Array.IndexOf(Invalid, c) >= 0 ? '_' : c);
        string name = sb.Length > 80 ? sb.ToString(0, 80) : sb.ToString();

        if (url.Query.Length > 1)   // ?page=2 and ?page=3 must not overwrite each other
        {
            byte[] hash = SHA256.HashData(Encoding.UTF8.GetBytes(url.Query));
            name += "_" + Convert.ToHexString(hash)[..8].ToLowerInvariant();
        }

        return name.EndsWith(".html", StringComparison.OrdinalIgnoreCase) ? name : name + ".html";
    }
}
""", "Downloader.Core/FileNames.cs")}
{C(r"""
namespace Downloader.Core;

public sealed record UrlListResult(IReadOnlyList<Uri> Urls, IReadOnlyList<string> Rejected);

public static class UrlList
{
    public static async Task<UrlListResult> LoadAsync(string path, CancellationToken ct = default)
    {
        var urls = new List<Uri>();
        var rejected = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        int lineNo = 0;

        await foreach (string raw in File.ReadLinesAsync(path, ct))       // .NET 7+: an async stream of lines
        {
            lineNo++;
            string line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;        // blank lines and comments

            if (!Uri.TryCreate(line, UriKind.Absolute, out Uri? uri) || uri.Scheme is not ("http" or "https"))
                rejected.Add($"line {lineNo}: not an http(s) URL → {line}");
            else if (!seen.Add(uri.AbsoluteUri))
                rejected.Add($"line {lineNo}: duplicate → {line}");
            else
                urls.Add(uri);
        }
        return new UrlListResult(urls, rejected);
    }
}
""", "Downloader.Core/UrlList.cs")}
{tip("The scheme check matters: on Linux and macOS, <code>Uri.TryCreate(\"/etc/passwd\", UriKind.Absolute, ...)</code> succeeds and produces a <code>file://</code> URI. Never let a URL list read local files.")}

<h3>Step 4 — PageDownloader: sequential, SemaphoreSlim and Parallel.ForEachAsync</h3>
{C(r"""
using System.Diagnostics;

namespace Downloader.Core;

public sealed class PageDownloader(IPageSource source, DownloadOptions options)
{
    // Baseline: one at a time
    public async Task<DownloadSummary> DownloadSequentialAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Directory.CreateDirectory(options.OutputDirectory);
        var sw = Stopwatch.StartNew();
        var results = new List<DownloadResult>(urls.Count);
        foreach (Uri url in urls)
            results.Add(await DownloadOneAsync(url, ct));
        return new DownloadSummary(results, sw.Elapsed);
    }

    // Strategy 1: start a task per URL, but let only MaxConcurrency past the gate at once
    public async Task<DownloadSummary> DownloadWithSemaphoreAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Directory.CreateDirectory(options.OutputDirectory);
        var sw = Stopwatch.StartNew();
        using var gate = new SemaphoreSlim(options.MaxConcurrency, options.MaxConcurrency);

        async Task<DownloadResult> ThrottledAsync(Uri url)
        {
            await gate.WaitAsync(ct);
            try { return await DownloadOneAsync(url, ct); }
            finally { gate.Release(); }
        }

        DownloadResult[] results = await Task.WhenAll(urls.Select(ThrottledAsync));   // results in input order
        return new DownloadSummary(results, sw.Elapsed);
    }

    // Strategy 2: let Parallel.ForEachAsync (.NET 6+) manage the workers
    public async Task<DownloadSummary> DownloadWithParallelAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Directory.CreateDirectory(options.OutputDirectory);
        var sw = Stopwatch.StartNew();
        var results = new DownloadResult[urls.Count];        // each index written by exactly one worker → no lock
        var po = new ParallelOptions { MaxDegreeOfParallelism = options.MaxConcurrency, CancellationToken = ct };

        await Parallel.ForEachAsync(Enumerable.Range(0, urls.Count), po, async (i, token) =>
        {
            results[i] = await DownloadOneAsync(urls[i], token);
        });
        return new DownloadSummary(results, sw.Elapsed);
    }

    private async Task<DownloadResult> DownloadOneAsync(Uri url, CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        try
        {
            PageContent page = await source.GetAsync(url, ct);
            if (page.StatusCode is < 200 or > 299)
                return new DownloadResult(url, DownloadStatus.Failed, sw.Elapsed, page.StatusCode, Error: $"HTTP {page.StatusCode}");

            string path = Path.Combine(options.OutputDirectory, FileNames.FromUrl(url));
            await File.WriteAllBytesAsync(path, page.Body, ct);
            return new DownloadResult(url, DownloadStatus.Succeeded, sw.Elapsed, page.StatusCode, page.Body.LongLength, path);
        }
        catch (OperationCanceledException) when (ct.IsCancellationRequested)
        {
            throw;                                            // the CALLER cancelled: stop the whole batch
        }
        catch (Exception ex) when (ex is HttpRequestException or OperationCanceledException or IOException or UnauthorizedAccessException)
        {
            // HttpRequestException: DNS / connection failure. OperationCanceledException (caller didn't cancel):
            // HttpClient.Timeout. IOException / UnauthorizedAccessException (read-only folder): couldn't write the file. One bad URL must not stop the rest.
            return new DownloadResult(url, DownloadStatus.Failed, sw.Elapsed, Error: ex.Message);
        }
    }
}
""", "Downloader.Core/PageDownloader.cs")}
<p>Why two concurrent strategies? They're the two idioms you'll meet in real code. <code>SemaphoreSlim</code> creates every task up front (cheap for hundreds of URLs, wasteful for millions) and gives an ordered array from WhenAll. <code>Parallel.ForEachAsync</code> keeps exactly N workers pulling items and needs you to store results yourself.</p>

<h3>Step 5 — Program.cs</h3>
{C(r"""
using System.Net;
using Downloader.Core;

string urlFile = args.Length > 0 && !args[0].StartsWith("--")
    ? args[0]
    : Path.Combine(AppContext.BaseDirectory, "urls.txt");    // the copy next to the .exe (dotnet run keeps YOUR working directory)
int maxConcurrency = IntOption("--max", 4);
bool offline = args.Contains("--offline");

UrlListResult list = await UrlList.LoadAsync(urlFile);
foreach (string bad in list.Rejected)
    Console.WriteLine($"  skipped {bad}");
if (list.Urls.Count == 0)
{
    Console.WriteLine("No valid URLs to download.");
    return 1;
}
Console.WriteLine($"{list.Urls.Count} URLs · max concurrency {maxConcurrency} · " +
                  (offline ? "offline (fake pages)" : "live HTTP") + "\n");

using HttpClient http = CreateHttpClient();
IPageSource source = offline ? new FakePageSource() : new HttpPageSource(http);

DownloadOptions Options(string mode) =>
    new() { MaxConcurrency = maxConcurrency, OutputDirectory = Path.Combine("downloads", mode) };

DownloadSummary seq = await new PageDownloader(source, Options("sequential")).DownloadSequentialAsync(list.Urls);
Print("Sequential", seq);

DownloadSummary sem = await new PageDownloader(source, Options("semaphore")).DownloadWithSemaphoreAsync(list.Urls);
Print($"SemaphoreSlim + WhenAll (max {maxConcurrency})", sem);

DownloadSummary par = await new PageDownloader(source, Options("parallel")).DownloadWithParallelAsync(list.Urls);
Print($"Parallel.ForEachAsync (max {maxConcurrency})", par);

Console.WriteLine($"Speed-up vs sequential: SemaphoreSlim {seq.Total / sem.Total:N1}x · " +
                  $"Parallel.ForEachAsync {seq.Total / par.Total:N1}x");
return 0;

int IntOption(string name, int fallback)
{
    int i = Array.IndexOf(args, name);
    return i >= 0 && i + 1 < args.Length && int.TryParse(args[i + 1], out int v) && v > 0 ? v : fallback;
}

static HttpClient CreateHttpClient()
{
    var handler = new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(2),
        AutomaticDecompression = DecompressionMethods.All      // accept gzip/brotli: fewer bytes on the wire
    };
    var http = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(30) };
    http.DefaultRequestHeaders.UserAgent.ParseAdd("DotnetLearningDownloader/1.0");   // some sites reject requests with no UA
    return http;
}

static void Print(string title, DownloadSummary s)
{
    Console.WriteLine($"== {title} ==");
    foreach (DownloadResult r in s.Results)
    {
        string mark = r.Success ? "OK  " : "FAIL";
        string detail = r.Success ? $"{r.Bytes,9:N0} bytes" : r.Error ?? "";
        Console.WriteLine($"  {mark} {r.Elapsed.TotalMilliseconds,6:N0} ms  {Short(r.Url.ToString()),-44} {detail}");
    }
    Console.WriteLine($"  {s.Succeeded} ok · {s.Failed} failed · {s.TotalBytes:N0} bytes · {s.Total.TotalSeconds:N2} s\n");
}

static string Short(string s) => s.Length <= 44 ? s : s[..41] + "...";
""", "Downloader.App/Program.cs")}
{C(r"""
# One URL per line. Blank lines and lines starting with # are ignored.
https://example.com/
https://learn.microsoft.com/en-us/dotnet/csharp/
https://www.python.org/
https://en.wikipedia.org/wiki/Bengaluru
https://en.wikipedia.org/wiki/Pune
https://www.isro.gov.in/
https://httpbin.org/delay/2
https://httpbin.org/status/404
https://httpbin.org/status/503
https://no-such-site.invalid/

not a url
https://example.com/
""", "Downloader.App/urls.txt", lang="text")}
<p><code>dotnet run --project ...</code> keeps your current folder as the working directory, so Program.cs looks for the default <code>urls.txt</code> in <code>AppContext.BaseDirectory</code> (the build output folder). Copy it there on every build:</p>
{C(r"""
<ItemGroup>
  <None Update="urls.txt" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
""", "Downloader.App/Downloader.App.csproj (add)", lang="xml")}

<h3>Run it</h3>
{C(r"""
dotnet run --project Downloader.App -- --offline          # works anywhere, no internet needed
dotnet run --project Downloader.App -- --max 8            # real downloads, 8 at a time
dotnet run --project Downloader.App -- my-urls.txt --max 2
""", lang="bash")}
{C(r"""
  skipped line 13: not an http(s) URL → not a url
  skipped line 14: duplicate → https://example.com/
10 URLs · max concurrency 4 · offline (fake pages)

== Sequential ==
  OK      944 ms  https://example.com/                             9,484 bytes
  OK      468 ms  https://learn.microsoft.com/en-us/dotnet/...     4,810 bytes
  OK    1,196 ms  https://www.python.org/                         12,061 bytes
  OK      709 ms  https://en.wikipedia.org/wiki/Bengaluru          7,208 bytes
  OK      370 ms  https://en.wikipedia.org/wiki/Pune               3,843 bytes
  OK    1,038 ms  https://www.isro.gov.in/                        10,483 bytes
  OK    3,140 ms  https://httpbin.org/delay/2                     11,442 bytes
  FAIL    730 ms  https://httpbin.org/status/404               HTTP 404
  FAIL    467 ms  https://httpbin.org/status/503               HTTP 503
  FAIL    425 ms  https://no-such-site.invalid/                Name or service not known (no-such-site.invalid:443)
  7 ok · 3 failed · 59,331 bytes · 9.49 s

== SemaphoreSlim + WhenAll (max 4) ==
  OK      892 ms  https://example.com/                             9,024 bytes
  OK      503 ms  https://learn.microsoft.com/en-us/dotnet/...     5,170 bytes
  OK      293 ms  https://www.python.org/                          3,030 bytes
  OK      955 ms  https://en.wikipedia.org/wiki/Bengaluru          9,658 bytes
  OK    1,169 ms  https://en.wikipedia.org/wiki/Pune              11,764 bytes
  OK      794 ms  https://www.isro.gov.in/                         8,052 bytes
  OK    2,788 ms  https://httpbin.org/delay/2                      7,961 bytes
  FAIL    748 ms  https://httpbin.org/status/404               HTTP 404
  FAIL    472 ms  https://httpbin.org/status/503               HTTP 503
  FAIL    494 ms  https://no-such-site.invalid/                Name or service not known (no-such-site.invalid:443)
  7 ok · 3 failed · 54,659 bytes · 3.68 s

== Parallel.ForEachAsync (max 4) ==
  OK      965 ms  https://example.com/                             9,734 bytes
  OK    1,171 ms  https://learn.microsoft.com/en-us/dotnet/...    11,841 bytes
  OK    1,090 ms  https://www.python.org/                         10,961 bytes
  OK      549 ms  https://en.wikipedia.org/wiki/Bengaluru          5,578 bytes
  OK      504 ms  https://en.wikipedia.org/wiki/Pune               5,163 bytes
  OK      537 ms  https://www.isro.gov.in/                         5,502 bytes
  OK    2,775 ms  https://httpbin.org/delay/2                      7,851 bytes
  FAIL    733 ms  https://httpbin.org/status/404               HTTP 404
  FAIL    247 ms  https://httpbin.org/status/503               HTTP 503
  FAIL    709 ms  https://no-such-site.invalid/                Name or service not known (no-such-site.invalid:443)
  7 ok · 3 failed · 56,630 bytes · 3.84 s

Speed-up vs sequential: SemaphoreSlim 2.6x · Parallel.ForEachAsync 2.5x
""", "Sample output (--offline; your timings will differ)", lang="text")}
<p>Read the numbers: sequential time is roughly the <i>sum</i> of every download; concurrent time is roughly the slowest \"wave\". With 10 URLs and a cap of 4 you get about three waves — and the <code>/delay/2</code> URL dominates one of them. Try <code>--max 1</code> (concurrent ≈ sequential) and <code>--max 20</code> (≈ the single slowest URL).</p>
{warn("Be polite with real sites: keep <code>--max</code> modest, don't hammer one host, and respect <code>robots.txt</code> and terms of use. Many sites rate-limit or block aggressive clients.", "Etiquette")}

<h3>Stretch goals</h3>
<ul>
<li>Stream large responses straight to disk with <code>HttpCompletionOption.ResponseHeadersRead</code> and <code>CopyToAsync</code> instead of buffering bytes (Thursday).</li>
<li>Add a per-host limit (at most 2 concurrent requests to the same host) with a <code>ConcurrentDictionary&lt;string, SemaphoreSlim&gt;</code>.</li>
<li>Write a CSV report (<code>url,status,ms,bytes,error</code>) alongside the downloads.</li>
<li>Print the page <code>&lt;title&gt;</code> of each download (a simple regex is fine for now).</li>
</ul>
''',
iqs=[("Basic","Why are concurrent downloads faster even on a single-core machine?","Downloading is I/O-bound: almost all the time is spent waiting for the network, during which no thread is busy. With async I/O, one core can have many requests in flight and handle each response as it arrives, so total time approaches the slowest request instead of the sum."),
("Basic","Why does DownloadOneAsync return a result instead of throwing for a 404 or DNS failure?","Failures of individual URLs are expected outcomes in a batch, not exceptional conditions for the whole run. Returning a DownloadResult keeps one bad URL from aborting the others (awaiting WhenAll would surface only one exception) and gives the report per-URL detail. Only caller cancellation is allowed to propagate."),
("Intermediate","SemaphoreSlim + Task.WhenAll vs Parallel.ForEachAsync for this tool — which would you choose?","Both cap concurrency. SemaphoreSlim + WhenAll creates all tasks immediately and returns results in input order — simple and fine for hundreds of URLs. Parallel.ForEachAsync keeps a fixed number of workers pulling from the source, so it scales to huge or streaming inputs (IAsyncEnumerable) with constant memory, but you store results yourself. For a big crawl I'd pick Parallel.ForEachAsync."),
("Intermediate","Is writing results[i] from many workers in Parallel.ForEachAsync thread-safe?","Yes, because each index is written by exactly one worker and array element writes don't interfere with each other; the array itself isn't resized. Adding to a shared List&lt;T&gt; instead would be a race. The completed ForEachAsync task also guarantees all writes are visible to the code after the await.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Cancellation, timeouts, retries, progress — and revision",
"Make the downloader production-shaped: Ctrl+C cancels cleanly and still reports what finished, each request has its own timeout, transient failures are retried with exponential backoff, and progress is shown live. Then document it, push it and revise the week.",
[("Graceful shutdown","Stopping on request (Ctrl+C) by cancelling work cooperatively, finishing or abandoning in-flight items, and still reporting results."),
("Console.CancelKeyPress","Event raised on Ctrl+C / Ctrl+Break. Setting <code>e.Cancel = true</code> stops the process from terminating immediately."),
("Transient fault","A temporary failure likely to succeed on retry: timeouts, connection resets, 408, 429, 502, 503, 504."),
("Exponential backoff","Waiting longer between each retry (e.g. 0.5 s, 1 s, 2 s) so a struggling server gets breathing room."),
("Jitter","A small random addition to each backoff delay so many clients don't all retry at the same instant."),
("IProgress&lt;T&gt;","Interface with one method, <code>Report(T value)</code>, for publishing progress from work to whoever displays it."),
("Progress&lt;T&gt;","Built-in IProgress&lt;T&gt; that invokes a handler on the SynchronizationContext captured when it was created — or on the thread pool if there wasn't one."),
("Idempotent","Safe to repeat: doing it twice has the same effect as once. GET requests are; \"charge ₹500\" is not — only retry idempotent operations blindly.")],
["Ctrl+C → cancel the token; work stops at the next await; the summary still prints.",
"A linked token per attempt gives each request its own timeout while still honouring Ctrl+C.",
"Retry only transient failures, a limited number of times, with growing delays and jitter.",
"In a console app <code>Progress&lt;T&gt;</code> runs handlers on pool threads — possibly concurrently and out of order. A tiny custom IProgress&lt;T&gt; that prints synchronously under a lock keeps lines from interleaving.",
"Polly (Week 43) does retries, timeouts and circuit breakers properly; writing a simple version first shows you what it's doing."],
f'''
<h3>1. New options and progress type</h3>
{C(r"""
namespace Downloader.Core;

public sealed record DownloadOptions
{
    public int MaxConcurrency { get; init; } = 4;
    public string OutputDirectory { get; init; } = "downloads";
    public TimeSpan PerRequestTimeout { get; init; } = TimeSpan.FromSeconds(10);
    public int MaxRetries { get; init; } = 2;                         // so up to 3 attempts in total
    public TimeSpan BaseRetryDelay { get; init; } = TimeSpan.FromMilliseconds(500);
}

public readonly record struct DownloadProgress(int Completed, int Total, DownloadResult Last);
""", "Downloader.Core/DownloadOptions.cs")}

<h3>2. PageDownloader with cancellation, per-request timeout, retry and progress</h3>
{C(r"""
using System.Diagnostics;

namespace Downloader.Core;

public sealed class PageDownloader(IPageSource source, DownloadOptions options, IProgress<DownloadProgress>? progress = null)
{
    private int _completed;

    public async Task<DownloadSummary> DownloadSequentialAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Prepare();
        var sw = Stopwatch.StartNew();
        var results = new List<DownloadResult>(urls.Count);
        foreach (Uri url in urls)
            results.Add(await DownloadOneAsync(url, urls.Count, ct));    // after Ctrl+C these return "cancelled" instantly
        return new DownloadSummary(results, sw.Elapsed);
    }

    public async Task<DownloadSummary> DownloadWithSemaphoreAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Prepare();
        var sw = Stopwatch.StartNew();
        using var gate = new SemaphoreSlim(options.MaxConcurrency, options.MaxConcurrency);

        async Task<DownloadResult> ThrottledAsync(Uri url)
        {
            try { await gate.WaitAsync(ct); }
            catch (OperationCanceledException) { return Report(DownloadResult.Cancelled(url), urls.Count); }   // never got a slot
            try { return await DownloadOneAsync(url, urls.Count, ct); }
            finally { gate.Release(); }
        }

        DownloadResult[] results = await Task.WhenAll(urls.Select(ThrottledAsync));
        return new DownloadSummary(results, sw.Elapsed);
    }

    public async Task<DownloadSummary> DownloadWithParallelAsync(IReadOnlyList<Uri> urls, CancellationToken ct = default)
    {
        Prepare();
        var sw = Stopwatch.StartNew();
        var results = new DownloadResult[urls.Count];
        // No token in ParallelOptions on purpose: every item still runs and records "cancelled",
        // so the summary is complete instead of ForEachAsync throwing away partial results
        var po = new ParallelOptions { MaxDegreeOfParallelism = options.MaxConcurrency };

        await Parallel.ForEachAsync(Enumerable.Range(0, urls.Count), po, async (i, _) =>
        {
            results[i] = await DownloadOneAsync(urls[i], urls.Count, ct);
        });
        return new DownloadSummary(results, sw.Elapsed);
    }

    private void Prepare()
    {
        Directory.CreateDirectory(options.OutputDirectory);
        Interlocked.Exchange(ref _completed, 0);
    }

    private async Task<DownloadResult> DownloadOneAsync(Uri url, int total, CancellationToken ct) =>
        Report(await DownloadWithRetryAsync(url, ct), total);

    private DownloadResult Report(DownloadResult result, int total)
    {
        int done = Interlocked.Increment(ref _completed);              // many workers finish at once
        progress?.Report(new DownloadProgress(done, total, result));
        return result;
    }

    private async Task<DownloadResult> DownloadWithRetryAsync(Uri url, CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        string? lastError = null;
        int? lastStatus = null;
        int attempts = 0;

        while (attempts <= options.MaxRetries)
        {
            if (ct.IsCancellationRequested) return DownloadResult.Cancelled(url, sw.Elapsed, attempts);
            attempts++;

            // One token per attempt: fires on Ctrl+C (ct) OR when this attempt's time is up
            using var attemptCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            attemptCts.CancelAfter(options.PerRequestTimeout);

            try
            {
                PageContent page = await source.GetAsync(url, attemptCts.Token);
                if (page.StatusCode is >= 200 and <= 299)
                {
                    string path = Path.Combine(options.OutputDirectory, FileNames.FromUrl(url));
                    await File.WriteAllBytesAsync(path, page.Body, ct);
                    return new DownloadResult(url, DownloadStatus.Succeeded, sw.Elapsed,
                        page.StatusCode, page.Body.LongLength, path, Attempts: attempts);
                }

                lastStatus = page.StatusCode;
                lastError = $"HTTP {page.StatusCode}";
                if (!IsTransient(page.StatusCode)) break;               // 404, 403…: retrying won't help
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                return DownloadResult.Cancelled(url, sw.Elapsed, attempts);   // Ctrl+C
            }
            catch (OperationCanceledException)
            {
                lastError = $"timed out after {options.PerRequestTimeout.TotalSeconds:0.#} s";   // our timeout
            }
            catch (HttpRequestException ex)
            {
                lastError = ex.Message;                                  // DNS failure, connection refused/reset
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)   // a read-only folder throws the latter
            {
                lastError = $"disk error: {ex.Message}";                 // not transient: don't retry
                break;
            }

            if (attempts <= options.MaxRetries)
            {
                try { await Task.Delay(Backoff(attempts), ct); }
                catch (OperationCanceledException) { return DownloadResult.Cancelled(url, sw.Elapsed, attempts); }
            }
        }

        return new DownloadResult(url, DownloadStatus.Failed, sw.Elapsed, lastStatus, Error: lastError, Attempts: attempts);
    }

    // 408 Request Timeout, 429 Too Many Requests, and every 5xx are worth another try
    private static bool IsTransient(int statusCode) => statusCode is 408 or 429 or >= 500;

    // 500 ms, 1 s, 2 s, 4 s… plus 0–20% random jitter
    private TimeSpan Backoff(int attempt)
    {
        double ms = options.BaseRetryDelay.TotalMilliseconds * Math.Pow(2, attempt - 1);
        return TimeSpan.FromMilliseconds(ms + Random.Shared.NextDouble() * ms * 0.2);
    }
}
""", "Downloader.Core/PageDownloader.cs")}
{table(["Failure","Retried?","Why"],[
["DNS failure / connection refused (HttpRequestException)","Yes","Networks blip; but a permanently wrong host just fails after MaxRetries"],
["Per-request timeout","Yes","The server may have been briefly slow"],
["408, 429, 500, 502, 503, 504","Yes","Server-side or rate-limit conditions that often clear"],
["400, 401, 403, 404","No","The request itself is wrong; the answer won't change"],
["Disk write error","No","Retrying the download doesn't fix a full or read-only disk"],
["Ctrl+C","No","The user asked us to stop"]])}

<h3>3. Live progress</h3>
<p><code>Progress&lt;T&gt;</code> captures <code>SynchronizationContext.Current</code> when it's created. In a WinForms app that's the UI thread, so its handler can safely update a progress bar. In a console app there is none, so every <code>Report</code> is posted to the thread pool: handlers can run concurrently and out of order (you might see 7/10 printed before 6/10). For console output, a tiny synchronous implementation is clearer:</p>
{C(r"""
using Downloader.Core;

namespace Downloader.App;

/// <summary>Prints each report immediately, one at a time, in the order Report is called.</summary>
public sealed class ConsoleProgress : IProgress<DownloadProgress>
{
    private readonly object _sync = new();        // on .NET 9: private readonly Lock _sync = new();

    public void Report(DownloadProgress p)
    {
        lock (_sync)                               // workers report from many threads at once
        {
            (string mark, ConsoleColor color) = p.Last.Status switch
            {
                DownloadStatus.Succeeded => ("✓", ConsoleColor.Green),
                DownloadStatus.Failed    => ("✗", ConsoleColor.Red),
                _                        => ("–", ConsoleColor.DarkYellow)
            };
            Console.ForegroundColor = color;
            Console.Write($"  [{p.Completed,2}/{p.Total}] {mark} ");
            Console.ResetColor();
            string tries = p.Last.Attempts > 1 ? $" · {p.Last.Attempts} attempts" : "";
            string info = p.Last.Success ? $"{p.Last.Bytes:N0} bytes" : p.Last.Error ?? "";
            Console.WriteLine($"{p.Last.Url} ({p.Last.Elapsed.TotalMilliseconds:N0} ms{tries}) {info}");
        }
    }
}
""", "Downloader.App/ConsoleProgress.cs")}

<h3>4. Program.cs with Ctrl+C and new options</h3>
{C(r"""
using System.Globalization;
using System.Net;
using System.Text;
using Downloader.App;
using Downloader.Core;

Console.OutputEncoding = Encoding.UTF8;               // ✓ ✗ symbols on Windows terminals

string urlFile = args.Length > 0 && !args[0].StartsWith("--")
    ? args[0]
    : Path.Combine(AppContext.BaseDirectory, "urls.txt");    // the copy next to the .exe (dotnet run keeps YOUR working directory)
int maxConcurrency = IntOption("--max", 4, min: 1);
int timeoutSeconds = IntOption("--timeout", 10, min: 1);
int retries        = IntOption("--retries", 2, min: 0);
string mode        = StringOption("--mode", "compare");   // compare | sequential | semaphore | parallel
bool offline       = args.Contains("--offline");
double failRate    = DoubleOption("--fail-rate", 0);      // offline only: fraction of fake 503s

if (!File.Exists(urlFile))
{
    Console.WriteLine($"URL file not found: {Path.GetFullPath(urlFile)}");
    return 2;
}

// Ctrl+C: first press cancels gracefully, second press lets the process die immediately
using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) =>
{
    if (cts.IsCancellationRequested) return;          // second Ctrl+C → default behaviour (terminate)
    e.Cancel = true;                                  // first Ctrl+C → keep the process alive...
    Console.WriteLine("\n  Cancelling… in-flight downloads will stop (Ctrl+C again to force quit)");
    cts.Cancel();                                     // ...and ask all work to stop
};

UrlListResult list = await UrlList.LoadAsync(urlFile, cts.Token);
foreach (string bad in list.Rejected)
    Console.WriteLine($"  skipped {bad}");
if (list.Urls.Count == 0)
{
    Console.WriteLine("No valid URLs to download.");
    return 1;
}

var options = new DownloadOptions
{
    MaxConcurrency = maxConcurrency,
    PerRequestTimeout = TimeSpan.FromSeconds(timeoutSeconds),
    MaxRetries = retries
};
Console.WriteLine($"{list.Urls.Count} URLs · max {maxConcurrency} · timeout {timeoutSeconds} s · " +
                  $"retries {retries} · {(offline ? "offline" : "live HTTP")}");

using HttpClient http = CreateHttpClient();
IPageSource source = offline ? new FakePageSource(transientFailureRate: failRate) : new HttpPageSource(http);
var progress = new ConsoleProgress();

string[] modes = mode == "compare" ? ["sequential", "semaphore", "parallel"] : [mode];
var runs = new List<(string Mode, DownloadSummary Summary)>();

foreach (string m in modes)
{
    if (cts.IsCancellationRequested) break;
    Console.WriteLine($"\n== {m} ==");
    var downloader = new PageDownloader(source, options with { OutputDirectory = Path.Combine("downloads", m) }, progress);

    DownloadSummary summary = m switch
    {
        "sequential" => await downloader.DownloadSequentialAsync(list.Urls, cts.Token),
        "semaphore"  => await downloader.DownloadWithSemaphoreAsync(list.Urls, cts.Token),
        "parallel"   => await downloader.DownloadWithParallelAsync(list.Urls, cts.Token),
        _ => throw new ArgumentException($"Unknown --mode '{m}'. Use compare, sequential, semaphore or parallel.")
    };
    Console.WriteLine($"  {summary.Succeeded} ok · {summary.Failed} failed · {summary.Cancelled} cancelled · " +
                      $"{summary.TotalBytes:N0} bytes · {summary.Total.TotalSeconds:N2} s");
    runs.Add((m, summary));
}

if (runs.Count > 1)
{
    Console.WriteLine("\n== Comparison ==");
    TimeSpan baseline = runs[0].Summary.Total;
    foreach (var (m, s) in runs)
        Console.WriteLine($"  {m,-11} {s.Total.TotalSeconds,6:N2} s   {baseline / s.Total,4:N1}x");
}

return cts.IsCancellationRequested ? 130 : 0;        // 130 = conventional "terminated by Ctrl+C" exit code

int IntOption(string name, int fallback, int min)
{
    int i = Array.IndexOf(args, name);
    return i >= 0 && i + 1 < args.Length && int.TryParse(args[i + 1], out int v) && v >= min ? v : fallback;
}

double DoubleOption(string name, double fallback)
{
    int i = Array.IndexOf(args, name);
    return i >= 0 && i + 1 < args.Length &&
           double.TryParse(args[i + 1], NumberStyles.Float, CultureInfo.InvariantCulture, out double v) &&
           v is >= 0 and <= 1 ? v : fallback;
}

string StringOption(string name, string fallback)
{
    int i = Array.IndexOf(args, name);
    return i >= 0 && i + 1 < args.Length ? args[i + 1].ToLowerInvariant() : fallback;
}

static HttpClient CreateHttpClient()
{
    var handler = new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(2),
        AutomaticDecompression = DecompressionMethods.All
    };
    // Our per-request timeout is in DownloadOptions, so switch off HttpClient's own 100 s default
    var http = new HttpClient(handler) { Timeout = Timeout.InfiniteTimeSpan };
    http.DefaultRequestHeaders.UserAgent.ParseAdd("DotnetLearningDownloader/1.0");
    return http;
}
""", "Downloader.App/Program.cs")}
{C(r"""
dotnet run --project Downloader.App -- --offline --mode semaphore --fail-rate 0.4 --timeout 1
""", lang="bash")}
{C(r"""
  skipped line 13: not an http(s) URL → not a url
  skipped line 14: duplicate → https://example.com/
10 URLs · max 4 · timeout 1 s · retries 2 · offline

== semaphore ==
  [ 1/10] ✓ https://en.wikipedia.org/wiki/Bengaluru (497 ms) 4,858 bytes
  [ 2/10] ✓ https://learn.microsoft.com/en-us/dotnet/csharp/ (581 ms) 5,940 bytes
  [ 3/10] ✓ https://en.wikipedia.org/wiki/Pune (819 ms) 8,293 bytes
  [ 4/10] ✓ https://www.isro.gov.in/ (1,161 ms · 2 attempts) 2,212 bytes
  [ 5/10] ✓ https://example.com/ (2,134 ms · 2 attempts) 5,794 bytes
  [ 6/10] ✗ https://httpbin.org/status/404 (826 ms) HTTP 404
  [ 7/10] ✓ https://www.python.org/ (3,714 ms · 3 attempts) 3,670 bytes
  [ 8/10] ✗ https://httpbin.org/delay/2 (4,685 ms · 3 attempts) timed out after 1 s
  [ 9/10] ✗ https://httpbin.org/status/503 (4,196 ms · 3 attempts) HTTP 503
  [10/10] ✗ https://no-such-site.invalid/ (3,941 ms · 3 attempts) Name or service not known (no-such-site.invalid:443)
  6 ok · 4 failed · 0 cancelled · 30,767 bytes · 6.53 s
""", "Sample output (offline, 40% fake 503s, 1 s timeout)", lang="text")}
<p>Notice <code>/delay/2</code> timing out on every attempt with a 1-second limit, the 503s being retried (some recover, the permanent <code>/status/503</code> never does), and the 404 failing after a single attempt. Because the fake latency is 200–1200 ms, a 1-second limit can also time out an ordinary page now and then; it is simply retried.</p>

<h3>5. Try to break it</h3>
{table(["Scenario","Expected"],[
["<code>urls.txt</code> missing","\"URL file not found: …\" with the full path, exit code 2"],
["File with only comments and blank lines","\"No valid URLs to download.\", exit code 1"],
["Lines <code>not a url</code>, <code>/etc/passwd</code>, <code>ftp://files.example.com</code>","Each reported as \"not an http(s) URL\" with its line number; never downloaded"],
["Same URL twice","Second one reported as duplicate"],
["<code>--max 0</code>, <code>--max abc</code>","Falls back to 4"],
["<code>--max 50</code> with 10 URLs","Works; total ≈ the slowest single URL"],
["<code>/status/404</code>","FAIL HTTP 404 after 1 attempt (not retried)"],
["<code>/status/503</code>","FAIL HTTP 503 after 3 attempts with growing delays"],
["<code>--timeout 1</code> with <code>/delay/2</code>","\"timed out after 1 s\" after 3 attempts"],
["Live mode with Wi-Fi off","Every URL fails fast with a DNS/connection error (after retries); no crash. Use <code>--offline</code>"],
["Ctrl+C halfway through","Remaining URLs marked cancelled, summary still printed, exit code 130"],
["Ctrl+C twice","Process terminates immediately"],
["Output folder read-only","\"disk error: …\" for each URL, not retried"],
["Two URLs differing only in <code>?page=</code>","Saved as two files (hash suffix)"],
["Ctrl+C while a file is being written","A partial file may remain — fix as a stretch goal: write to <code>.part</code>, then <code>File.Move</code>"]])}

<h3>6. README and push</h3>
{C(r"""
# Async Web-Page Downloader

Micro-project 6 of my .NET full-stack roadmap (Week 7: async and concurrency).

## Features
- Reads URLs from a file (comments, blank lines, invalid and duplicate URLs handled)
- Downloads concurrently with a configurable limit, two ways:
  `SemaphoreSlim` + `Task.WhenAll`, and `Parallel.ForEachAsync`
- Compares sequential vs concurrent timing; reports bytes, successes and failures
- Ctrl+C cancels gracefully and still prints a summary
- Per-request timeout, retry with exponential backoff + jitter for transient errors
- Live progress via `IProgress<T>`
- `--offline` mode with a fake page source (no internet needed)

## Usage
```bash
dotnet run --project Downloader.App -- [urls.txt] [--max 4] [--timeout 10] [--retries 2]
                                       [--mode compare|sequential|semaphore|parallel]
                                       [--offline] [--fail-rate 0.3]
```

## What I learned
async/await, Task.WhenAll, CancellationToken and linked tokens, SemaphoreSlim,
Parallel.ForEachAsync, Interlocked, IAsyncEnumerable (File.ReadLinesAsync),
HttpClient lifetime, transient-fault handling, IProgress<T>
""", "README.md", lang="markdown")}
{C(r"""
cd Downloader
dotnet new gitignore
echo "downloads/" >> .gitignore           # don't commit downloaded pages
git init
git add .
git commit -m "Async downloader: concurrency limit, cancellation, timeouts, retries, progress"
git branch -M main
git remote add origin https://github.com/<your-username>/async-downloader.git
git push -u origin main
""", lang="bash")}

<h3>7. Week 7 revision checklist</h3>
<ul>
<li>Thread vs thread pool vs Task; why tasks are the default</li>
<li>CPU-bound (Task.Run, Parallel) vs I/O-bound (async APIs); concurrency vs parallelism</li>
<li>Task states; exceptions stored in tasks; await vs .Wait() (AggregateException); unobserved exceptions</li>
<li>ValueTask: when, and its four rules</li>
<li>What await does step by step; the compiler state machine; where continuations run</li>
<li>SynchronizationContext per app type; ConfigureAwait(false) in libraries; none in ASP.NET Core</li>
<li>The .Result deadlock; async all the way; async void only for event handlers (and hidden async void lambdas)</li>
<li>WhenAll (results in order, one rethrown exception vs all exceptions), WhenAny, .NET 9 WhenEach</li>
<li>CancellationTokenSource vs CancellationToken; cooperative cancellation; OperationCanceledException</li>
<li>Timeouts: CancelAfter, linked tokens, WaitAsync; telling timeout from cancellation</li>
<li>HttpClient lifetime, socket exhaustion, PooledConnectionLifetime, IHttpClientFactory; status codes; what to retry</li>
<li>IAsyncEnumerable, await foreach, async iterators, [EnumeratorCancellation]</li>
<li>Race conditions; lock and .NET 9 Lock; Interlocked; ConcurrentDictionary pitfalls; SemaphoreSlim; Parallel APIs; deadlock prevention</li>
</ul>

<h3>8. Quick quiz — predict the output</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
Console.Write("A");
Task t = WorkAsync();
Console.Write("C");
await t;
Console.Write("E");

static async Task WorkAsync()
{
    Console.Write("B");
    await Task.Delay(100);
    Console.Write("D");
}
""")}<b>ABCDE.</b> WorkAsync runs synchronously until its first await on an incomplete task, so B prints before the call returns. Then C prints while the delay runs, D after it, and E once <code>t</code> completes.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
Task<int> t = GetAsync();
Console.Write("3");
Console.Write(await t);

static async Task<int> GetAsync()
{
    Console.Write("1");
    await Task.CompletedTask;     // already complete
    Console.Write("2");
    return 4;
}
""")}<b>1234.</b> Awaiting an already-completed task doesn't pause: the method runs straight through (1, 2) and returns a completed task before the caller prints 3.</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
try { Boom(); }
catch (Exception) { Console.Write("caught "); }
await Task.Delay(500);
Console.Write("end");

static async void Boom()
{
    await Task.Yield();
    throw new InvalidOperationException("boom");
}
""")}<b>Nothing — the process crashes</b> with an unhandled InvalidOperationException. <code>Boom</code> returns at its first await, so the try block finishes without error; the exception is later thrown on a thread-pool thread where nobody can catch it. That's why async void is only for event handlers.</details>
<details><summary>Q4. What prints?</summary>
{C(r"""
Task all = Task.WhenAll(FailAsync("A", 300), FailAsync("B", 100));
try { await all; }
catch (Exception ex) { Console.Write($"{ex.Message} {all.Exception!.InnerExceptions.Count}"); }

static async Task FailAsync(string message, int delayMs)
{
    await Task.Delay(delayMs);
    throw new InvalidOperationException(message);
}
""")}<b>B 2</b> on .NET 8 — but only the <b>2</b> is guaranteed. WhenAll waits for both tasks and collects both exceptions; <code>await</code> rethrows just one of them. On .NET 8 the non-generic <code>Task.WhenAll</code> records failures in completion order (B failed first, after 100 ms), whereas <code>WhenAll&lt;T&gt;</code> uses argument order, so never write code that depends on which exception you get. The full list is in <code>all.Exception.InnerExceptions</code>.</details>
<details><summary>Q5. What prints?</summary>
{C(r"""
try { int n = ParseAsync("abc").Result; }
catch (FormatException) { Console.Write("F"); }
catch (AggregateException) { Console.Write("A"); }

try { int n = await ParseAsync("abc"); }
catch (FormatException) { Console.Write("F"); }
catch (AggregateException) { Console.Write("A"); }

static async Task<int> ParseAsync(string s)
{
    await Task.Delay(10);
    return int.Parse(s);
}
""")}<b>AF.</b> <code>.Result</code> (like <code>.Wait()</code>) wraps the failure in an AggregateException; <code>await</code> unwraps it and rethrows the original FormatException. (In a console app the blocking call doesn't deadlock — there's no SynchronizationContext — but it still blocks a thread.)</details>

<div class="note tip"><b>Next week:</b> Week 8 — .NET internals. What really happens under all this async code: the CLR and JIT (tiered compilation), stack vs heap, how the garbage collector works (generations, LOH, workstation vs server GC), IDisposable, <code>using</code> and finalizers, <code>Span&lt;T&gt;</code>/<code>Memory&lt;T&gt;</code> for allocation-free code, and measuring it all with BenchmarkDotNet.</div>
''',
iqs=[("Basic","How do you handle Ctrl+C gracefully in a .NET console app?","Create a CancellationTokenSource, subscribe to Console.CancelKeyPress, set e.Cancel = true so the process isn't killed, and call cts.Cancel(). Pass the token through all async work so it stops at the next await, then let the program print what finished and exit with a suitable code. Hosted apps (Generic Host) do this for you via IHostApplicationLifetime."),
("Intermediate","Which failures should you retry, and why use exponential backoff with jitter?","Only transient ones: network errors, timeouts, 408, 429 and 5xx — and only for idempotent operations, or ones protected by an idempotency key. Backoff gives an overloaded server time to recover instead of hammering it; jitter spreads retries from many clients so they don't all hit the server at the same instant (thundering herd). Always cap the number of attempts."),
("Intermediate","How does the downloader tell a per-request timeout from a user cancellation?","Each attempt uses a CTS linked to the user's token with CancelAfter(timeout). When OperationCanceledException is thrown, an exception filter checks the user's token: if it's cancelled, the user pressed Ctrl+C and the item is marked cancelled; otherwise the attempt timed out, which is treated as transient and retried."),
("Intermediate","What's the difference between Progress&lt;T&gt; and a custom IProgress&lt;T&gt; in a console app?","Progress&lt;T&gt; posts each Report to the SynchronizationContext captured at construction. In UI apps that marshals to the UI thread, which is what you want. Console apps have no context, so handlers are queued to the thread pool and can run concurrently or out of order. A custom IProgress&lt;T&gt; that runs the handler synchronously under a lock prints each report immediately and never interleaves lines (counter numbers can still, rarely, appear one out of order, because two workers may increment before either takes the lock).")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Threads, tasks and the thread pool","Threads &amp; tasks","Thread vs Task, CPU- vs I/O-bound, concurrency vs parallelism, task exceptions, ValueTask.","2 hrs"),
 (2,"TUE","async/await under the hood","async/await","State machine, continuations, SynchronizationContext, ConfigureAwait, no .Result, async void.","2 hrs"),
 (3,"WED","WhenAll, WhenAny, cancellation and timeouts","WhenAll &amp; cancellation","Run work concurrently, collect every exception, CancellationToken, CancelAfter, WaitAsync.","2 hrs"),
 (4,"THU","HttpClient and async streams","HttpClient &amp; streams","Shared HttpClient, status codes, timeouts, IHttpClientFactory, IAsyncEnumerable.","2 hrs"),
 (5,"FRI","Thread safety and parallelism","Thread safety","Races, lock and .NET 9 Lock, Interlocked, concurrent collections, SemaphoreSlim, Parallel, deadlocks.","2 hrs"),
 (6,"SAT","Micro-project 6: Async web-page downloader","Project: downloader","Concurrent downloads with SemaphoreSlim and Parallel.ForEachAsync; sequential vs concurrent timing.","4 hrs"),
 (7,"SUN","Cancellation, retries, progress and revision","Resilience &amp; revision","Ctrl+C, per-request timeouts, retry with backoff, IProgress, README, async-ordering quiz.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week07.html", 7,
      "Week 7 — Async and concurrency", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 7 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Micro-project 6"],
      "Every web API, database call and file read you write from now on will be async. This week you'll learn what tasks and threads really are, exactly what <code>await</code> does, how to run work concurrently, cancel it and time it out, call HTTP APIs properly, and keep shared data safe when many threads touch it. You'll finish with a concurrent web-page downloader that handles timeouts, retries and Ctrl+C.",
      cards, days)
print("built")
