import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "CLR, IL, JIT, assemblies and NuGet packages",
"Explain what happens between writing C# and the CPU running it, read a little IL, know your JIT and AOT options, and manage NuGet dependencies safely.",
[("CLR","Common Language Runtime: the virtual machine that loads assemblies, JIT-compiles IL, manages memory with the GC, enforces type safety and handles exceptions and threads."),
("IL / CIL","Intermediate Language: the CPU-independent, stack-based instruction set the C# compiler (Roslyn) emits into a .dll."),
("JIT compiler","Just-In-Time compiler (RyuJIT) that turns a method's IL into native machine code the first time the method is called."),
("Tiered compilation","On by default since .NET Core 3.0: methods first get a quick, unoptimised Tier 0 compile; hot methods (called ~30 times) are recompiled in the background at optimised Tier 1."),
("Dynamic PGO","Profile-Guided Optimisation at runtime: Tier 0 code records which types and branches are actually used, and Tier 1 optimises for them. On by default in .NET 8."),
("OSR","On-Stack Replacement (.NET 7+): lets a long-running loop inside a Tier 0 method jump into optimised code without waiting for the method to be called again."),
("ReadyToRun (R2R)","Ahead-of-time pre-compiled native code stored inside the assembly alongside IL, to cut startup JIT time. The JIT can still re-optimise hot methods."),
("Native AOT","Publishing the whole app as one native executable with no JIT and no IL at runtime (.NET 7+ for console apps, .NET 8 adds ASP.NET Core minimal APIs). Fast startup, small memory, but limited reflection and no dynamic code."),
("Assembly","The unit of deployment and versioning in .NET: a .dll or .exe containing IL, metadata and a manifest."),
("Metadata","Tables inside an assembly describing every type, method, field, attribute and reference. Reflection and IntelliSense read it."),
("Manifest","Part of the metadata describing the assembly itself: name, version, culture and the assemblies it references."),
("NuGet package","A .nupkg (zip) containing compiled assemblies per target framework plus a .nuspec describing its dependencies."),
("PackageReference","The csproj item that declares a NuGet dependency: <code>&lt;PackageReference Include=\"Serilog\" Version=\"4.0.0\" /&gt;</code>."),
("Transitive dependency","A package you get indirectly because a package you referenced depends on it."),
("Central Package Management","Declaring all package versions once in <code>Directory.Packages.props</code> so every project in a solution uses the same version.")],
["C# → (Roslyn) → IL in a .dll → (CLR loads it) → JIT → native code. Only the last step is CPU-specific.",
"The same .dll runs on Windows, Linux and macOS because it contains IL, not machine code.",
"Every .NET language (C#, F#, VB) compiles to the same IL, which is why they can call each other.",
"Tier 0 → Tier 1 is why the first few calls of a method are slower; always warm up before measuring.",
"<code>Version=\"8.0.0\"</code> in a PackageReference means <b>8.0.0 or higher</b> (minimum), and NuGet picks the lowest version that satisfies it.",
"Run <code>dotnet list package --vulnerable --include-transitive</code> regularly; the .NET 8 SDK also audits on restore and warns (NU1901–NU1904)."],
f'''
<h3>1. From C# to running code</h3>
<p>The C# compiler never produces machine code. It produces IL plus metadata. When you run the app, the host (<code>dotnet</code> or the app's own launcher) starts the CLR, which loads the assembly, verifies types, and JIT-compiles each method on its first call.</p>
{table(["Step","Who does it","Output"],[
["1. Compile","Roslyn (<code>dotnet build</code>)","<code>Toolkit.dll</code> with IL + metadata, <code>Toolkit.pdb</code> debug symbols"],
["2. Describe","SDK","<code>Toolkit.deps.json</code> (dependencies) and <code>Toolkit.runtimeconfig.json</code> (which runtime, GC settings)"],
["3. Start","Host (<code>dotnet Toolkit.dll</code> or <code>Toolkit.exe</code>)","Finds and starts the right runtime version"],
["4. Load","CLR","Reads the manifest, loads referenced assemblies on demand"],
["5. JIT","RyuJIT","Native code for each method, the first time it's called"],
["6. Run","CPU + CLR services","GC, exceptions, threads, type checks"]])}
{C(r"""
dotnet new console -n Toolkit && cd Toolkit
dotnet build -c Release
ls bin/Release/net8.0/
# Toolkit            ← native launcher (apphost) for your OS
# Toolkit.dll        ← your IL + metadata: this is the real program
# Toolkit.pdb        ← debug symbols (line numbers in stack traces)
# Toolkit.deps.json  ← resolved dependency graph
# Toolkit.runtimeconfig.json  ← target runtime + runtime settings

cat bin/Release/net8.0/Toolkit.runtimeconfig.json
# {
#   "runtimeOptions": {
#     "tfm": "net8.0",
#     "framework": { "name": "Microsoft.NETCore.App", "version": "8.0.0" }
#   }
# }
""", lang="bash")}

<h3>2. Reading IL</h3>
<p>You'll rarely write IL, but reading it settles arguments like \"does this box?\" or \"what does this syntax compile to?\". IL is a <b>stack machine</b>: instructions push values onto an evaluation stack and pop them off.</p>
{C(r"""
public static class Gst
{
    public static int Add(int a, int b) => a + b;

    public static object Box(int amount) => amount;          // int → object
}
""", "Gst.cs")}
{C(r"""
// Gst.Add (Release build)
.method public hidebysig static int32 Add(int32 a, int32 b) cil managed
{
  .maxstack 8
  IL_0000: ldarg.0      // push a
  IL_0001: ldarg.1      // push b
  IL_0002: add          // pop both, push a + b
  IL_0003: ret          // return the top of the stack
}

// Gst.Box
.method public hidebysig static object Box(int32 amount) cil managed
{
  .maxstack 8
  IL_0000: ldarg.0
  IL_0001: box [System.Runtime]System.Int32   // ← the boxing allocation you learned about in Week 3
  IL_0006: ret
}
""", "IL (from ILSpy / sharplab.io)", lang="text")}
{table(["Tool","Use it for"],[
["<a href=\"https://sharplab.io\">sharplab.io</a>","Paste C#, instantly see IL, the lowered C# (what <code>foreach</code>, <code>using</code>, records, async really become) and JIT assembly. Best for learning."],
["ILSpy (free, also a VS Code extension)","Open any .dll and decompile it back to C# or IL. Great for reading library code."],
["ildasm","Microsoft's classic IL disassembler (ships with Visual Studio / available as a dotnet tool)."],
["Visual Studio: Go To Definition on library code","Uses decompilation / Source Link to show the source of framework methods."]])}
{tip("Paste a <code>record</code>, a <code>foreach</code> over a <code>List&lt;T&gt;</code> and an <code>async</code> method into sharplab.io and switch the output to C#. Seeing the generated Equals, enumerator struct and state machine makes Weeks 3, 4 and 7 click.")}

<h3>3. The JIT: tiered compilation, PGO and OSR</h3>
{table(["Tier","When","Quality","Why"],[
["Tier 0","First call","Quick, minimally optimised","Start up fast; most methods are only called a few times"],
["Tier 0 instrumented","Hot methods (.NET 8 PGO)","Quick + records types/branches seen","Collect a profile of real usage"],
["Tier 1","After ~30 calls (background, after a short delay)","Fully optimised, uses the PGO profile","Fast steady-state performance"],
["OSR","A loop in Tier 0 code runs many iterations","Optimised version of the running method","Long loops don't stay slow (.NET 7+)"],
["ReadyToRun code","At startup, if the assembly was published R2R","Good, but not PGO-tuned","Skip JIT at startup; hot methods still go to Tier 1"]])}
{C(r"""
using System.Diagnostics;

static long GstTotal(int[] amounts)
{
    long total = 0;
    foreach (int a in amounts) total += a * 18 / 100;
    return total;
}

int[] amounts = Enumerable.Range(1, 100_000).ToArray();
for (int run = 1; run <= 5; run++)
{
    long start = Stopwatch.GetTimestamp();
    long result = 0;
    for (int i = 0; i < 50; i++) result += GstTotal(amounts);
    Console.WriteLine($"Run {run}: {Stopwatch.GetElapsedTime(start).TotalMilliseconds:N2} ms");   // GetElapsedTime: .NET 7+
    Thread.Sleep(200);                     // give the background Tier 1 compile a chance
}
// Early runs may execute Tier 0 code. On modern CPUs the gap is often small for loop-heavy methods: that's OSR doing its job.
// Try: DOTNET_TieredCompilation=0 dotnet run -c Release   (everything fully optimised up front, slower startup)
//      DOTNET_TieredPGO=0 dotnet run -c Release           (turn off Dynamic PGO)
""", "JitWarmup.cs")}
{C(r"""
<PropertyGroup>
  <TieredPGO>true</TieredPGO>                      <!-- default in .NET 8; set false to opt out -->
  <TieredCompilation>true</TieredCompilation>      <!-- rarely changed -->
</PropertyGroup>
""", "csproj (runtime knobs, awareness only)", lang="xml")}
{warn("Never benchmark a Debug build or the first call of a method. Debug disables JIT optimisations, and the first call measures JIT time. Use Release, warm up, and ideally BenchmarkDotNet (Saturday).", "Gotcha")}

<h3>4. ReadyToRun vs Native AOT</h3>
{C(r"""
# Normal framework-dependent publish: IL only, JIT at runtime
dotnet publish -c Release

# ReadyToRun: IL + pre-compiled native code for one runtime identifier (RID)
dotnet publish -c Release -r linux-x64 -p:PublishReadyToRun=true

# Native AOT (.NET 7+ console, .NET 8+ minimal APIs): one native executable, no JIT
dotnet publish -c Release -r linux-x64 -p:PublishAot=true
""", lang="bash")}
{table(["","JIT (default)","ReadyToRun","Native AOT"],[
["Startup","Slowest","Faster","Fastest"],
["Peak throughput","Best (Tier 1 + PGO)","Best after warm-up (hot code re-JITted)","Good, but no runtime PGO"],
["Output","Portable IL .dll","Larger .dll per RID","Single native file per RID"],
["Needs .NET runtime installed","Yes (unless self-contained)","Yes (unless self-contained)","No"],
["Reflection / dynamic code","Everything works","Everything works","Limited: trimming removes unused code, no <code>Reflection.Emit</code>, no loading assemblies at runtime"],
["Typical use","Most apps and APIs","Desktop apps, faster cold start","CLI tools, serverless/containers with fast scale-out, small microservices"]])}
{warn("Native AOT apps are trimmed. Code that discovers types by reflection (Thursday) or uses reflection-based JSON serialisation produces trim/AOT warnings and may fail at runtime. Treat those warnings as errors and use source generators instead.", "AOT")}

<h3>5. Assemblies and metadata</h3>
{C(r"""
using System.Reflection;

Assembly asm = Assembly.GetExecutingAssembly();
AssemblyName name = asm.GetName();

Console.WriteLine($"{name.Name} v{name.Version}");                       // Toolkit v1.0.0.0
Console.WriteLine(asm.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion);
                                                                          // 1.0.0 (.NET 8 SDK may append +<git commit hash>)
Console.WriteLine($"Types defined: {asm.GetTypes().Length}");

foreach (AssemblyName reference in asm.GetReferencedAssemblies())
    Console.WriteLine($"  references {reference.Name} {reference.Version}");
// references System.Runtime 8.0.0.0
// references System.Console 8.0.0.0
// ...

Console.WriteLine(typeof(string).Assembly.Location);    // .../shared/Microsoft.NETCore.App/8.0.x/System.Private.CoreLib.dll
""", "AssemblyInfo.cs")}
{C(r"""
<PropertyGroup>
  <Version>1.4.2</Version>                         <!-- sets all three below unless overridden -->
  <AssemblyVersion>1.0.0.0</AssemblyVersion>       <!-- what the CLR binds to; change rarely in libraries -->
  <FileVersion>1.4.2.0</FileVersion>               <!-- shown in Windows file properties -->
  <InformationalVersion>1.4.2-beta</InformationalVersion>  <!-- human-readable product version -->
</PropertyGroup>
""", "Toolkit.csproj", lang="xml")}

<h3>6. NuGet packages: references, versions, lock files, central management</h3>
{C(r"""
dotnet add package Serilog --version 4.0.0          # adds a PackageReference
dotnet add package Serilog.Sinks.Console
dotnet remove package Serilog.Sinks.Console
dotnet list package                                 # direct packages and resolved versions
dotnet list package --include-transitive            # plus everything they pulled in
dotnet list package --outdated                      # newer versions available
dotnet list package --vulnerable --include-transitive   # known CVEs (GitHub Advisory Database)
""", lang="bash")}
{table(["Version in PackageReference","Means"],[
["<code>8.0.0</code>","Minimum: 8.0.0 or higher; NuGet resolves the <b>lowest</b> available that satisfies everything"],
["<code>[8.0.0]</code>","Exactly 8.0.0"],
["<code>[8.0.0,9.0.0)</code>","8.0.0 inclusive up to 9.0.0 exclusive"],
["<code>(,9.0.0)</code>","Anything below 9.0.0"],
["<code>8.*</code>","Floating: the highest 8.x available at restore time (builds become non-repeatable)"]])}
<h4>Lock files: repeatable restores</h4>
{C(r"""
<PropertyGroup>
  <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>   <!-- writes packages.lock.json; commit it -->
</PropertyGroup>
""", "csproj", lang="xml")}
{C(r"""
dotnet restore --locked-mode     # in CI: fail if the lock file and the csproj disagree
""", lang="bash")}
<h4>Central Package Management (awareness)</h4>
{C(r"""
<!-- Directory.Packages.props at the solution root -->
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Serilog" Version="4.0.0" />
    <PackageVersion Include="xunit" Version="2.9.0" />
  </ItemGroup>
</Project>

<!-- Then in each project: no Version attribute -->
<ItemGroup>
  <PackageReference Include="Serilog" />
</ItemGroup>
""", "Directory.Packages.props", lang="xml")}
{tip("If two packages need different versions of the same dependency, NuGet picks the lowest version that satisfies all minimums. When a transitive package has a vulnerability, add a direct PackageReference (or a CPM <code>PackageVersion</code>) to a fixed version to override it.")}
''',
["Benchmarking a Debug build, or timing the first call that includes JIT compilation.",
"Thinking a .NET .dll contains machine code; it contains IL (unless published R2R, and even then IL is still there).",
"Using floating versions (<code>*</code>) in production projects, making builds non-repeatable.",
"Ignoring restore warnings NU1901–NU1904 about vulnerable packages.",
"Turning on Native AOT for an app full of reflection and ignoring the trim warnings."],
("35 min", ["Paste a small class with a <code>record</code>, a <code>foreach</code> over a List and a <code>string</code> interpolation into sharplab.io. Write down three things the compiler generated that you didn't write.",
"Run the JitWarmup sample in Release three ways: default, <code>DOTNET_TieredCompilation=0</code>, <code>DOTNET_TieredPGO=0</code>. Record run 1 and run 5 timings for each in a table.",
"In your Week 6/7 project run <code>dotnet list package --include-transitive</code>, <code>--outdated</code> and <code>--vulnerable</code>. Enable a lock file, commit it and run <code>dotnet restore --locked-mode</code>."]),
[("What does a .NET .dll actually contain?","IL code, metadata (type/member tables, attributes), a manifest (name, version, references) and optionally resources. Native code only if published ReadyToRun."),
("Why is the first call to a method slower?","The JIT compiles it at Tier 0 on first call. After about 30 calls it's recompiled at optimised Tier 1 in the background."),
("What does <code>Version=\"8.0.0\"</code> mean in a PackageReference?","A minimum version: 8.0.0 or higher, with NuGet choosing the lowest version that satisfies all constraints.")],
[("Basic","What is the CLR and what does it do?","The Common Language Runtime is .NET's execution engine. It loads assemblies, JIT-compiles IL to native code, manages memory with the garbage collector, enforces type safety, handles exceptions and provides threading and interop services."),
("Basic","What is IL and why does .NET use it?","Intermediate Language is the CPU-independent bytecode compilers emit. It makes assemblies portable across OS and CPU, lets all .NET languages interoperate, and lets the JIT optimise for the actual machine and the actual runtime behaviour."),
("Basic","What is an assembly?","The unit of deployment, versioning and security in .NET: a .dll or .exe containing IL, metadata describing all types and members, and a manifest with its identity and references."),
("Intermediate","Explain tiered compilation and Dynamic PGO.","Methods are first compiled quickly at Tier 0 for fast startup. Methods called often are recompiled in the background at Tier 1 with full optimisations. With Dynamic PGO (default in .NET 8), the Tier 0 code is instrumented to record actual types and branches, and Tier 1 uses that profile for things like guarded devirtualisation and hot/cold code layout."),
("Intermediate","ReadyToRun vs Native AOT?","ReadyToRun adds pre-compiled native code to normal assemblies to reduce startup JIT; IL is kept, the JIT still runs and re-optimises hot code, and all features work. Native AOT compiles the whole trimmed app into a single native executable with no JIT: fastest startup and smallest memory, but no runtime code generation, limited reflection, and a build per OS/architecture."),
("Intermediate","How do you keep NuGet dependencies safe and repeatable?","Pin explicit versions (no floating), use a lock file with <code>--locked-mode</code> in CI, use Central Package Management in multi-project solutions, audit with <code>dotnet list package --vulnerable --include-transitive</code> and the SDK's restore audit, and override vulnerable transitive packages with a direct reference to a patched version.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Stack vs heap, the managed heap and the garbage collector",
"Describe precisely where data lives, how the GC finds and frees garbage, how generations and the Large Object Heap work, and why finalizers are expensive.",
[("Stack","Per-thread memory holding method frames: parameters, locals and return addresses. Freed automatically when a method returns."),
("Managed heap","Memory the GC manages, holding every object (class instance, array, string, boxed value)."),
("Reference","A pointer-sized value that refers to an object on the heap."),
("GC root","A starting point the GC trusts is alive: live locals and parameters, static fields, GC handles, the f-reachable (ready-to-finalize) queue, CPU registers."),
("Reachable","An object that can be reached by following references from some root. Unreachable objects are garbage."),
("Mark / sweep / compact","The GC marks reachable objects, frees the rest, and usually slides survivors together to remove gaps."),
("Generation","Age bucket for objects: gen 0 (new), gen 1 (survived one GC), gen 2 (long-lived)."),
("Promotion","Moving a surviving object to the next generation after a collection."),
("Large Object Heap (LOH)","Separate heap for objects of 85,000 bytes or more. Logically part of gen 2, collected only in gen 2 GCs, not compacted by default."),
("Pinned Object Heap (POH)",".NET 5+ heap for objects that must never move (e.g. buffers passed to native code)."),
("Workstation vs Server GC","Workstation: one heap, tuned for low latency on client apps. Server: one heap and GC thread per core, tuned for throughput."),
("Background GC","The default concurrent mode: gen 2 collections run mostly alongside your threads; gen 0/1 still pause briefly."),
("Finalizer","A <code>~ClassName()</code> method the GC calls on a dedicated thread before reclaiming an object. A last-resort safety net for unmanaged resources."),
("Dispose","Deterministic cleanup via <code>IDisposable</code>, called by you or a <code>using</code> statement — the normal way to release resources.")],
["\"Value types live on the stack\" is a myth. Value types live <b>where their container lives</b>.",
"Allocation on the managed heap is very cheap (bump a pointer). Collection is the expensive part.",
"Most objects die young, so gen 0 collections are frequent and fast; gen 2 collections are rare and expensive.",
"Objects ≥ 85,000 bytes go straight to the LOH; repeatedly allocating them causes gen 2 GCs and fragmentation.",
"Don't call <code>GC.Collect()</code> in application code. The GC tunes itself far better than you can.",
"A finalizer makes every instance survive at least one extra GC. Implement <code>IDisposable</code> and call <code>GC.SuppressFinalize</code>."],
f'''
<h3>1. Stack vs heap, precisely</h3>
<p>The interview-safe statement: <b>reference-type objects always live on the heap. Value types live wherever their container is</b> — in a method's stack frame if they're a plain local or parameter, inside the object if they're a field, inside the array if they're array elements. Captured or hoisted locals move to the heap too.</p>
{C(r"""
public struct Money                 // value type
{
    public decimal Amount;
    public string Currency;         // a reference: the string object itself is on the heap
}

public class Order                  // reference type
{
    public int Id;                  // inside the Order object → heap
    public Money Total;             // struct field → stored INLINE inside the Order object → heap
}

public static class Where
{
    public static void Process()
    {
        int qty = 3;                                   // local → this method's stack frame (or a CPU register)
        Money price = new() { Amount = 499m, Currency = "INR" };   // whole struct in the frame; "INR" is a heap string
        Order order = new() { Id = 1 };                // the REFERENCE is in the frame; the Order object is on the heap
        int[] lines = [1, 2, 3];                       // one heap array object holding the ints inline
        object boxed = qty;                            // boxing: a new heap object holding a copy of 3

        int discount = 10;
        Func<int> getDiscount = () => discount;        // captured: `discount` becomes a field of a heap closure object
        Console.WriteLine(getDiscount() + price.Amount + order.Id + lines.Length + (int)boxed);
    }
}
""", "Where.cs")}
{table(["Data","Lives in"],[
["Local / parameter of value type (not captured)","Stack frame (or a register)"],
["Local / parameter of reference type","The reference in the frame; the object on the heap"],
["Field of a class (value or reference type)","Inside the object, on the heap"],
["Field of a struct","Wherever the struct is"],
["Array elements","Inside the array object, on the heap"],
["Locals captured by a lambda","In a compiler-generated closure object on the heap"],
["Locals in async methods (that live across an await) and iterators","In the state machine, which moves to the heap when the method suspends"],
["<code>stackalloc</code> buffers","Stack frame (Wednesday)"]])}
{warn("Saying \"structs are faster because they're on the stack\" in an interview invites follow-ups. Better: \"structs avoid a separate heap allocation and are copied by value; whether they're on the stack depends on where they're declared.\"", "Interview")}

<h3>2. How the GC decides what to free</h3>
<ol>
<li><b>Allocation:</b> the heap keeps a pointer to the next free byte. <code>new</code> just bumps it, which is why allocation is almost as cheap as a stack push.</li>
<li><b>Trigger:</b> when gen 0's budget is used up (or memory is low, or you call GC.Collect), a collection starts.</li>
<li><b>Mark:</b> starting from roots, follow every reference and mark what's reachable.</li>
<li><b>Sweep / compact:</b> everything unmarked is garbage. Survivors are usually slid together and references updated, so the free space is one contiguous block again.</li>
<li><b>Promote:</b> survivors of a gen 0 GC become gen 1; survivors of a gen 1 GC become gen 2.</li>
</ol>
<p>Circular references are not a problem: two objects pointing at each other but unreachable from any root are both garbage. .NET's GC is a tracing GC, not reference counting.</p>
{C(r"""
static void BuildReport()
{
    var customer = new Customer("Asha");          // reachable via the local `customer`
    customer.Orders.Add(new CustomerOrder(1, customer));   // the order points back: a cycle
    Console.WriteLine(customer.Orders.Count);
}   // after this returns nothing roots either object → both are collectable, cycle or not

record Customer(string Name) { public List<CustomerOrder> Orders { get; } = []; }
record CustomerOrder(int Id, Customer Owner);
""")}

<h3>3. Generations and measuring them</h3>
<p>The <b>generational hypothesis</b>: most objects die young (request DTOs, LINQ iterators, temporary strings), and objects that survive a while tend to live a long time (caches, singletons). So the GC collects gen 0 often and cheaply, and touches gen 2 rarely.</p>
{C(r"""
var invoice = new byte[1_000];
Console.WriteLine(GC.GetGeneration(invoice));   // 0 — brand new

GC.Collect();                                   // learning only!
Console.WriteLine(GC.GetGeneration(invoice));   // 1 — survived, promoted
GC.Collect();
Console.WriteLine(GC.GetGeneration(invoice));   // 2 — long-lived now
GC.KeepAlive(invoice);

Console.WriteLine($"gen0={GC.CollectionCount(0)} gen1={GC.CollectionCount(1)} gen2={GC.CollectionCount(2)}");

// Measuring memory
long heapNow     = GC.GetTotalMemory(forceFullCollection: false);  // approx bytes currently in use on the heap
long allocThread = GC.GetAllocatedBytesForCurrentThread();         // total ever allocated by THIS thread
long allocTotal  = GC.GetTotalAllocatedBytes(precise: false);      // total ever allocated by the process

GCMemoryInfo info = GC.GetGCMemoryInfo();
Console.WriteLine($"Heap {info.HeapSizeBytes / 1024 / 1024} MB, fragmented {info.FragmentedBytes / 1024} KB, " +
                  $"time paused in GC {info.PauseTimePercentage}%");
""", "Generations.cs")}
{table(["","Gen 0","Gen 1","Gen 2 (+ LOH)"],[
["Holds","New objects","Survived one GC: a buffer between young and old","Long-lived objects, LOH objects"],
["Collected","Very often","Whenever gen 1 or 2 is collected","Rarely (a \"full GC\")"],
["Cost","Small: few survivors to copy","Small","Large: the whole heap is examined"],
["Smell","—","—","Many gen 2 GCs = objects living just long enough to be promoted, or LOH churn"]])}
{tip("Use <code>GC.GetAllocatedBytesForCurrentThread()</code> before and after a piece of code to see exactly how much it allocates. It's how you'll compare Substring vs Span on Saturday.")}

<h3>4. The Large Object Heap</h3>
{C(r"""
var small = new byte[84_000];
var large = new byte[85_000];
Console.WriteLine(GC.GetGeneration(small));   // 0
Console.WriteLine(GC.GetGeneration(large));   // 2 — LOH objects are reported as gen 2 from birth

// The threshold is the OBJECT size, header included (24 bytes for an array on 64-bit):
// new byte[84_975] → 84,999 bytes → small object heap
// new byte[84_976] → 85,000 bytes → LOH
// new double[10_700] → 85,624 bytes → LOH ; a List<int> grown to 25,000 ints by Add has capacity 32,768 → a 131,072-byte internal array → LOH
""")}
<ul>
<li>LOH objects are only collected in gen 2 collections, so churning them (e.g. a new 1 MB buffer per request) forces expensive full GCs.</li>
<li>The LOH isn't compacted by default (copying big blocks is expensive), so it can fragment. You can request a one-off compaction with <code>GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce</code>.</li>
<li>Fixes: reuse buffers with <code>ArrayPool&lt;T&gt;</code> (Wednesday), stream data instead of loading it all, and pre-size collections sensibly.</li>
</ul>

<h3>5. GC modes and GC.Collect</h3>
{table(["Setting","Default","Effect"],[
["Workstation GC","Console, desktop apps","One heap; GC runs on the thread that triggered it; lower memory"],
["Server GC","ASP.NET Core apps (Web SDK sets it)","One heap + dedicated GC thread per logical core; higher throughput, more memory"],
["Background (concurrent) GC","On","Gen 2 collections run concurrently with your code; shorter pauses"],
["DATAS","Opt-in in .NET 8, on by default with Server GC in .NET 9","Server GC that grows and shrinks the number of heaps with load, cutting memory use in containers"]])}
{C(r"""
<PropertyGroup>
  <ServerGarbageCollection>true</ServerGarbageCollection>
  <ConcurrentGarbageCollection>true</ConcurrentGarbageCollection>
</PropertyGroup>
<!-- or at runtime without rebuilding: environment variable DOTNET_gcServer=1 -->
""", "csproj", lang="xml")}
{C(r"""
using System.Runtime;
Console.WriteLine(GCSettings.IsServerGC);     // False in a console app by default
Console.WriteLine(GCSettings.LatencyMode);    // Interactive (= background GC on)
""")}
<h4>Why not GC.Collect()?</h4>
<ul>
<li>It forces a full, blocking gen 2 collection: the most expensive kind.</li>
<li>It promotes everything still alive into older generations, making later collections more expensive.</li>
<li>It throws away the GC's own tuning, which is based on actual allocation rates.</li>
<li>Acceptable: tests and experiments (like this week's lab), benchmarks between iterations, and very rare cases like right after loading a huge one-time dataset in a desktop app, after measuring.</li>
</ul>

<h3>6. Finalizers and why they're costly</h3>
{C(r"""
using System.Runtime.InteropServices;

// Only needed when YOU own an unmanaged resource directly (rare; prefer SafeHandle)
public class NativeReportBuffer : IDisposable
{
    private IntPtr _memory = Marshal.AllocHGlobal(64 * 1024);   // unmanaged: the GC knows nothing about it
    private bool _disposed;

    public void Dispose()
    {
        Dispose(disposing: true);
        GC.SuppressFinalize(this);          // already cleaned up → skip the finalizer, skip the extra GC
    }

    protected virtual void Dispose(bool disposing)
    {
        if (_disposed) return;
        if (disposing)
        {
            // dispose other managed IDisposables here (only when called from Dispose)
        }
        Marshal.FreeHGlobal(_memory);       // always release the unmanaged resource
        _memory = IntPtr.Zero;
        _disposed = true;
    }

    ~NativeReportBuffer() => Dispose(disposing: false);   // safety net if someone forgets Dispose
}

// Typical class: wraps managed IDisposables only → NO finalizer needed
public sealed class InvoiceWriter(string path) : IDisposable
{
    private readonly StreamWriter _writer = new(path);    // FileStream's SafeFileHandle has its own finalizer
    public void WriteLine(string line) => _writer.WriteLine(line);
    public void Dispose() => _writer.Dispose();
}
""", "Finalizers.cs")}
<p>What a finalizer costs:</p>
<ol>
<li>At allocation, the object is registered on the <b>finalization queue</b> (slower allocation).</li>
<li>When it becomes unreachable, the GC can't free it. It moves it to the <b>f-reachable queue</b> — which is a root — so the object and everything it references <b>survive and get promoted</b>.</li>
<li>A single finalizer thread runs finalizers one by one, in no guaranteed order.</li>
<li>Only a <b>later</b> GC (often gen 1 or 2 by now) actually frees the memory.</li>
<li>In .NET Core / .NET 5+, finalizers are not run on process exit, so they can't be relied on for flushing data.</li>
</ol>
<p class="muted">On a 2-core cloud VM with .NET 8, allocating and collecting 1,000,000 tiny objects took around 1 ms without a finalizer and roughly 150–300 ms with an empty one (approximate; varies by machine, but the gap is always large).</p>
''',
["Repeating \"value types go on the stack, reference types go on the heap\" without the caveats.",
"Calling <code>GC.Collect()</code> to \"fix\" memory usage instead of finding what keeps objects alive.",
"Allocating large temporary buffers (≥ 85 KB) in a loop or per request.",
"Adding a finalizer to a class that only holds managed objects.",
"Forgetting <code>GC.SuppressFinalize(this)</code> in Dispose when the class does have a finalizer."],
("35 min", ["Write a program that prints <code>GC.GetGeneration</code> for a new object, then after one and two <code>GC.Collect()</code> calls. Then do the same for <code>new byte[100_000]</code> and explain the difference.",
"Allocate 10 million short-lived <code>Order</code> records in a loop and print the collection counts for gen 0/1/2 before and after. Then keep every 100th one in a list and compare.",
"Measure with <code>GC.GetAllocatedBytesForCurrentThread</code> how many bytes <code>string.Join</code>, <code>+=</code> in a loop and <code>StringBuilder</code> allocate for 1,000 words."]),
[("Where does an int field of a class live?","On the heap, inside the object. Value types are stored inline in their container."),
("Why does the LOH cause performance problems?","LOH objects are only collected with gen 2 (full) GCs and the LOH isn't compacted by default, so churn causes expensive collections and fragmentation."),
("Why should Dispose call GC.SuppressFinalize?","Because the resource is already released; suppressing removes the object from the finalization queue so it can be freed in the next GC without waiting for the finalizer thread.")],
[("Basic","Where are value types and reference types stored?","Reference-type objects are always on the managed heap; variables hold references to them. Value types are stored inline where they're declared: in the stack frame for non-captured locals and parameters, inside the object for fields, inside the array for elements. Captured locals and async/iterator locals are hoisted to heap objects."),
("Basic","How does the .NET garbage collector work?","It's a generational, tracing, compacting GC. When gen 0's budget is used it marks objects reachable from roots (locals, statics, handles), frees the rest, compacts survivors and promotes them to the next generation. Gen 0 is collected often and cheaply, gen 2 rarely."),
("Basic","What is the Large Object Heap?","A separate area for objects of 85,000 bytes or more. It's logically part of gen 2, so those objects are only collected during full GCs, and it isn't compacted by default to avoid copying large blocks."),
("Intermediate","Why shouldn't you call GC.Collect()?","It forces an expensive blocking full collection, promotes still-live objects to older generations (making future GCs costlier) and overrides the GC's self-tuning. It's acceptable in tests, benchmarks and rare measured scenarios."),
("Intermediate","Workstation vs Server GC?","Workstation GC uses one heap and collects on the triggering thread, minimising memory and pause times for client apps. Server GC creates one heap and GC thread per logical core and collects in parallel, maximising throughput for servers at the cost of more memory. ASP.NET Core apps use Server GC by default; .NET 9 enables DATAS to adapt heap count to load."),
("Intermediate","What's the difference between Dispose and a finalizer?","Dispose is deterministic: called by your code or a using statement as soon as you're done. A finalizer is non-deterministic: run by the finalizer thread some time after the object becomes unreachable, makes the object survive an extra GC, and isn't run at process exit in modern .NET. Use Dispose for cleanup and a finalizer only as a safety net for directly owned unmanaged resources (preferably via SafeHandle).")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Span&lt;T&gt;, Memory&lt;T&gt;, stackalloc and ArrayPool&lt;T&gt;",
"Slice strings and arrays without copying, parse text without allocations, and reuse buffers — knowing exactly where spans can and can't be used.",
[("Span&lt;T&gt;","A type-safe view over a contiguous block of memory (array, string, stack or native memory) that can be read and written without copying."),
("ReadOnlySpan&lt;T&gt;","The read-only version; what you get from a string via <code>AsSpan()</code>."),
("ref struct","A struct that can only live on the stack. Span&lt;T&gt; is one, which is why it has restrictions."),
("Slice","A smaller span over part of the same memory: <code>span.Slice(2, 5)</code> or <code>span[2..7]</code>. No copying."),
("Range / Index","<code>a..b</code> and <code>^1</code> (from the end) syntax, working on arrays, strings and spans."),
("stackalloc","Allocates a small buffer in the current stack frame; freed automatically when the method returns. Safe when assigned to a Span."),
("Memory&lt;T&gt;","Like Span but a normal struct, so it can be stored in fields and used across <code>await</code>. Get a span from it with <code>.Span</code>."),
("ReadOnlyMemory&lt;T&gt;","The read-only version of Memory&lt;T&gt;."),
("ArrayPool&lt;T&gt;","A shared pool of arrays: <code>Rent</code> one, use it, <code>Return</code> it, instead of allocating a new array each time."),
("TryFormat","<code>ISpanFormattable</code> method that writes a value's text into a span instead of creating a string."),
("MemoryExtensions","Static class with span methods: IndexOf, StartsWith, Trim, Split (.NET 8), Count (.NET 8), SequenceEqual…"),
("Zero-allocation","Code that does its work without creating heap objects, so it creates no GC pressure.")],
["A span is a pointer + a length. Slicing just changes those two numbers.",
"<code>Substring</code> allocates a new string; <code>AsSpan(start, length)</code> doesn't.",
"Most parsing APIs accept spans: <code>int.Parse(ReadOnlySpan&lt;char&gt;)</code>, <code>decimal.TryParse</code>, <code>DateOnly.ParseExact</code>.",
"Span can't be a field of a class, can't be boxed, can't be captured by a lambda, and can't cross an <code>await</code>. Use Memory&lt;T&gt; there.",
"stackalloc only small, bounded sizes (a few hundred bytes to ~1 KB). Never a size that comes from user input.",
"Every <code>Rent</code> needs a <code>Return</code> in a <code>finally</code>; the rented array may be bigger than you asked for."],
f'''
<h3>1. What a span is</h3>
{C(r"""
int[] marks = [72, 88, 95, 61, 79];
Span<int> lastThree = marks.AsSpan(2);         // 95, 61, 79 — a window onto the array, not a copy
lastThree[0] = 99;                             // writes through to the array
Console.WriteLine(marks[2]);                   // 99

string pan = "ABCDE1234F";
ReadOnlySpan<char> letters = pan.AsSpan(0, 5); // "ABCDE", no new string
ReadOnlySpan<char> digits  = pan.AsSpan()[5..9];   // "1234"
Console.WriteLine(int.Parse(digits) + 1);      // 1235 — parsed straight from the span
Console.WriteLine(letters.ToString());         // ABCDE — ToString() allocates; do it only when you need a string

string sub = pan.Substring(5, 4);              // ❌ allocates a new 4-char string every call
""", "SpanBasics.cs")}
{table(["","string / Substring","ReadOnlySpan&lt;char&gt;","Memory&lt;T&gt;"],[
["Allocates on slicing","Yes (new string)","No","No"],
["Can be a class field","Yes","No","Yes"],
["Usable across await","Yes","No","Yes"],
["Can wrap stack memory","No","Yes (stackalloc)","No"],
["Typical use","Values you store and pass around","Parsing and hot loops inside one method","Async I/O buffers, storing a slice for later"]])}

<h3>2. Parsing without allocations</h3>
<p>A GSTIN has 15 characters: a 2-digit state code, the 10-character PAN, an entity number, the letter Z and a check character. Validating thousands of them per second (e.g. an invoice import) with Substring creates several strings each. With spans it creates none until you decide to keep something.</p>
{C(r"""
Console.WriteLine(Gstin.TryParse("  29ABCDE1234F1Z5 ", out var g));   // True
Console.WriteLine(g);                                                // GstinInfo { StateCode = 29, Pan = ABCDE1234F, EntityNumber = 1 }
Console.WriteLine(Gstin.TryParse("29ABCDE12X4F1Z5", out _));         // False

public readonly record struct GstinInfo(int StateCode, string Pan, char EntityNumber);

public static class Gstin
{
    // e.g. 29ABCDE1234F1Z5 → state 29 (Karnataka), PAN ABCDE1234F, entity 1
    public static bool TryParse(ReadOnlySpan<char> input, out GstinInfo info)
    {
        info = default;
        ReadOnlySpan<char> s = input.Trim();                     // span Trim: no new string
        if (s.Length != 15 || s[13] != 'Z') return false;

        if (!int.TryParse(s[..2], out int state) || state is < 1 or > 38) return false;   // simplified range

        ReadOnlySpan<char> pan = s.Slice(2, 10);
        if (!IsPan(pan)) return false;

        info = new GstinInfo(state, pan.ToString(), s[12]);     // the only allocation, and only on success
        return true;
    }

    private static bool IsPan(ReadOnlySpan<char> p)
    {
        foreach (char c in p[..5]) if (!char.IsAsciiLetterUpper(c)) return false;   // .NET 7+
        foreach (char c in p[5..9]) if (!char.IsAsciiDigit(c)) return false;
        return char.IsAsciiLetterUpper(p[9]);
    }
}

""", "Gstin.cs")}
<h4>Splitting a CSV line without Split()</h4>
{C(r"""
using System.Globalization;

ReadOnlySpan<char> line = "EMP-104,Priya Sharma,Pune,85000";

Span<Range> parts = stackalloc Range[5];      // one extra slot so we can detect too many fields
int count = line.Split(parts, ',');           // MemoryExtensions.Split: .NET 8+
if (count == 4)
{
    ReadOnlySpan<char> city = line[parts[2]];
    decimal salary = decimal.Parse(line[parts[3]], CultureInfo.InvariantCulture);
    Console.WriteLine($"{city} {salary:N0}");  // Pune 85,000   (city is formatted directly, no extra string)
}

// string.Split would allocate a string[] plus 4 strings for every line
""", "CsvSpan.cs")}

<h3>3. stackalloc and formatting into spans</h3>
{C(r"""
static string InvoiceNumber(int branch, int sequence)
{
    Span<char> buffer = stackalloc char[32];                // on the stack, freed on return
    if (!buffer.TryWrite($"INV-{branch:D3}-{sequence:D6}", out int written))   // MemoryExtensions.TryWrite: .NET 6+
        throw new InvalidOperationException("Buffer too small");
    return new string(buffer[..written]);                  // the one allocation: the final string
}
Console.WriteLine(InvoiceNumber(7, 4521));                 // INV-007-004521

// Lower level: each number writes itself into the span
Span<char> date = stackalloc char[10];
new DateOnly(2026, 11, 10).TryFormat(date, out int n, "yyyy-MM-dd");
Console.WriteLine(date[..n].ToString());                   // 2026-11-10
""", "StackallocDemo.cs")}
{C(r"""
using System.Buffers;

// Size not known in advance: stack for small inputs, pool for big ones
static int CountVowels(string text)
{
    const int MaxStack = 256;
    char[]? rented = null;
    Span<char> lower = text.Length <= MaxStack
        ? stackalloc char[MaxStack]
        : (rented = ArrayPool<char>.Shared.Rent(text.Length));
    try
    {
        int len = text.AsSpan().ToLowerInvariant(lower);   // writes into our buffer, no new string
        int vowels = 0;
        foreach (char c in lower[..len]) if ("aeiou".Contains(c)) vowels++;
        return vowels;
    }
    finally
    {
        if (rented is not null) ArrayPool<char>.Shared.Return(rented);
    }
}
Console.WriteLine(CountVowels("Thiruvananthapuram"));    // 7
""", "HybridBuffer.cs")}
{warn("<code>stackalloc</code> with a large or user-controlled size can throw a <code>StackOverflowException</code>, which kills the process and can't be caught. Keep it small and constant, and fall back to ArrayPool.", "Danger")}

<h3>4. ref struct restrictions</h3>
<p>Span&lt;T&gt; may point at stack memory. If it could escape to the heap, it could outlive the stack frame it points into. So the compiler keeps every <code>ref struct</code> on the stack:</p>
{C(r"""
public class ImportJob
{
    // private Span<char> _buffer;                 // ❌ CS8345: a class field lives on the heap
    private Memory<char> _buffer = new char[1024];  // ✓ Memory<T> is allowed in fields

    public void Process()
    {
        Span<char> span = _buffer.Span;           // ✓ get a span when you're about to work synchronously
        span[0] = 'A';

        // object boxed = span;                   // ❌ can't box a ref struct
        // Func<int> f = () => span.Length;       // ❌ CS8175: can't capture in a lambda
        // var list = new List<Span<char>>();     // ❌ can't be a generic type argument
                                                  //    (C# 13 / .NET 9 adds `allows ref struct` for APIs that opt in)
    }

    // public async Task SaveAsync(Span<byte> data) { }   // ❌ CS4012: async parameters can't be ref structs
    //   C# 12: also no Span LOCALS in async methods. C# 13 allows them if they're not used across an await.
}

// You can write your own ref struct — e.g. a zero-allocation line reader
public ref struct LineReader(ReadOnlySpan<char> text)
{
    private ReadOnlySpan<char> _rest = text;

    public bool TryReadLine(out ReadOnlySpan<char> line)
    {
        if (_rest.IsEmpty) { line = default; return false; }
        int nl = _rest.IndexOf('\n');
        line = nl < 0 ? _rest : _rest[..nl];
        _rest = nl < 0 ? default : _rest[(nl + 1)..];
        return true;
    }
}
""", "RefStructRules.cs")}
{C(r"""
var reader = new LineReader("Mumbai,400001\nDelhi,110001\nChennai,600001");
while (reader.TryReadLine(out var row))
    Console.WriteLine(row[(row.IndexOf(',') + 1)..].ToString());   // 400001, 110001, 600001
""")}

<h3>5. Memory&lt;T&gt; for async code</h3>
{C(r"""
using System.Buffers;

static async Task<int> CountLinesAsync(Stream stream, CancellationToken ct = default)
{
    byte[] buffer = ArrayPool<byte>.Shared.Rent(81_920);       // asks for 80 KB; Shared rounds up to a 128 KB array (LOH), but it is reused, not reallocated
    try
    {
        int lines = 0, read;
        while ((read = await stream.ReadAsync(buffer.AsMemory(), ct)) > 0)   // Memory<byte> crosses the await
            lines += buffer.AsSpan(0, read).Count((byte)'\n');               // span used between awaits only (Count: .NET 8)
        return lines;
    }
    finally
    {
        ArrayPool<byte>.Shared.Return(buffer);
    }
}

await using var file = File.OpenRead("orders.csv");
Console.WriteLine(await CountLinesAsync(file));
""", "CountLinesAsync.cs")}

<h3>6. ArrayPool&lt;T&gt; rules</h3>
{C(r"""
using System.Buffers;

byte[] rented = ArrayPool<byte>.Shared.Rent(100_000);
Console.WriteLine(rented.Length);            // 131072 — rounded up to a bucket size: use only what you asked for
try
{
    Span<byte> work = rented.AsSpan(0, 100_000);
    work.Fill(0);                            // rented arrays are NOT cleared: may contain a previous user's data
    // ... use work ...
}
finally
{
    ArrayPool<byte>.Shared.Return(rented, clearArray: true);   // clear if it held personal data (PAN, card numbers)
}
// rented[0] = 1;                            // ❌ never touch an array after returning it
""", "ArrayPoolRules.cs")}
{table(["Situation","Reach for"],[
["Look at part of a string/array in a method","<code>AsSpan()</code> + slicing"],
["Parse numbers/dates out of text","Span overloads of Parse/TryParse"],
["Build a small string from parts","<code>string.Create</code>, interpolation, or stackalloc + TryWrite"],
["Temporary buffer ≤ ~1 KB, fixed size","<code>stackalloc</code>"],
["Temporary buffer, large or variable size","<code>ArrayPool&lt;T&gt;.Shared</code>"],
["Buffer passed to async I/O or stored in a field","<code>Memory&lt;T&gt;</code>"],
["Ordinary business code that isn't hot","Plain strings and arrays — clarity first"]])}
{tip("Spans are an optimisation for hot paths: parsers, serializers, middleware, loops over millions of rows. Measure first (Saturday). In a CRUD controller called 10 times a second, Substring is fine.")}
''',
["Calling <code>.ToString()</code> on every slice, which brings back the allocations you were avoiding.",
"Using the full length of a rented array instead of the length you asked for.",
"Forgetting to Return a rented array (no try/finally), or using it after returning it.",
"<code>stackalloc</code> with a size derived from input, risking a stack overflow.",
"Trying to store a Span in a field or use it across <code>await</code> instead of switching to Memory&lt;T&gt;."],
("35 min", ["Write <code>bool TryParsePin(ReadOnlySpan&lt;char&gt; s, out int pin)</code> that accepts 6 digits, first digit 1–9, optionally with one space after 3 digits (\"560 001\"). Measure allocations for 100,000 calls.",
"Parse <code>\"2026-11-10|Rahul Verma|2499.50|UPI\"</code> into a record using only span operations, and confirm with <code>GC.GetAllocatedBytesForCurrentThread</code> that only the record and the name string are allocated.",
"Write a method that reads a file in 80 KB chunks with ArrayPool and Memory&lt;byte&gt; and counts how many times the byte for ',' appears."]),
[("Why can't Span&lt;T&gt; be a field in a class?","Because a span may point to stack memory; a class lives on the heap and could outlive that stack frame. ref structs are restricted to the stack."),
("When do you use Memory&lt;T&gt; instead of Span&lt;T&gt;?","When the buffer must be stored in a field, captured, or used across an await — typically async I/O."),
("What must you remember about ArrayPool.Rent?","The array may be larger than requested and isn't cleared; always Return it in a finally block and never use it afterwards.")],
[("Basic","What is Span&lt;T&gt; and why was it introduced?","A ref struct representing a contiguous region of memory (array, string, stack or native) with type safety and bounds checks. It enables slicing and parsing without copying or allocating, which reduces GC pressure in hot paths."),
("Basic","What is the difference between Span&lt;T&gt; and Memory&lt;T&gt;?","Span is a ref struct: stack-only, very fast, can wrap stackalloc memory, but can't be a field, boxed, captured or used across await. Memory is a regular struct that can live on the heap and cross awaits; you get a Span from it with .Span when you do synchronous work."),
("Basic","What is ArrayPool&lt;T&gt; for?","Reusing arrays instead of allocating new ones, which avoids GC work and especially LOH churn for big buffers. Rent returns an array of at least the requested length; Return gives it back."),
("Intermediate","What are the restrictions on ref structs and why?","They can't be boxed, be fields of classes or normal structs, be captured by lambdas, be generic type arguments (until C# 13's allows ref struct), or be async-method parameters or (before C# 13) locals in async methods or iterators. All of these could move the value to the heap, where it could outlive the stack memory it refers to."),
("Intermediate","How would you parse a large CSV with minimal allocations?","Stream the file (StreamReader or PipeReader) rather than loading it, process each line as a ReadOnlySpan&lt;char&gt;, find fields with IndexOf or MemoryExtensions.Split into a stackalloc'd Range buffer, parse with span overloads of int/decimal/DateOnly.Parse, and only create strings for values you keep. Reuse buffers with ArrayPool."),
("Intermediate","When is stackalloc safe to use?","For small, bounded buffers (typically up to a few hundred bytes to ~1 KB) assigned to a Span&lt;T&gt;, which needs no unsafe code. For large or input-dependent sizes, use the hybrid pattern: stackalloc below a threshold, ArrayPool above it, because a stack overflow can't be caught.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Reflection and attributes",
"Inspect types at runtime, create objects and call methods dynamically, write and read your own attributes, and know what reflection costs and what replaces it.",
[("Reflection","Reading metadata and working with types, members and objects at runtime via <code>System.Reflection</code>."),
("Type","The runtime description of a type: name, members, base type, interfaces, attributes."),
("typeof vs GetType()","<code>typeof(Employee)</code> gets a Type at compile time; <code>obj.GetType()</code> gets the actual runtime type of an instance."),
("MemberInfo","Base class for PropertyInfo, FieldInfo, MethodInfo, ConstructorInfo, EventInfo."),
("PropertyInfo","Describes a property; <code>GetValue</code>/<code>SetValue</code> read and write it on an instance."),
("MethodInfo","Describes a method; <code>Invoke</code> calls it with an object[] of arguments."),
("BindingFlags","Filters for which members to return: Public, NonPublic, Instance, Static, DeclaredOnly."),
("Activator.CreateInstance","Creates an object from a Type at runtime, optionally with constructor arguments."),
("Attribute","A class deriving from <code>System.Attribute</code> whose instances are stored as metadata on code elements."),
("AttributeUsage","Attribute on an attribute class saying where it can be applied and whether it can be repeated or inherited."),
("Custom attribute","Your own attribute, e.g. <code>[Range(18, 60)]</code>, read back by reflection or a source generator."),
("Source generator","A compiler plug-in that generates C# at build time, replacing runtime reflection with ordinary fast code."),
("Trimming","Removing unused code when publishing (needed for Native AOT). Reflection can break it because the trimmer can't see what you'll look up by name.")],
["Reflection is how serializers, DI containers, ORMs, test frameworks and model validation work.",
"Attributes do nothing by themselves; something must read them.",
"Attribute constructor arguments must be compile-time constants: numbers, strings, bool, enums, Type, or arrays of those. Not decimal or DateTime.",
"Reflection is often 10x or more slower than a direct call per member access, and the lookup itself costs more: cache PropertyInfo/MethodInfo.",
"Reading private members via reflection breaks encapsulation; acceptable in tools and tests, not in business logic.",
"Modern .NET prefers source generators (System.Text.Json, Regex, logging) for speed and AOT compatibility."],
f'''
<h3>1. Getting and inspecting a Type</h3>
{C(r"""
public class Employee
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string City { get; set; } = "";
    public decimal MonthlySalary { get; set; }
    private string _pan = "";

    public decimal AnnualCtc() => MonthlySalary * 12;
    public string Greet(string greeting) => $"{greeting}, {Name}";
    private string MaskedPan() => _pan.Length == 10 ? $"XXXXX{_pan[5..]}" : "";
}

public class Manager : Employee
{
    public int TeamSize { get; set; }
}
""", "Employee.cs")}
{C(r"""
Type t1 = typeof(Employee);                    // compile time
Employee e = new Manager();
Type t2 = e.GetType();                         // runtime type: Manager, not Employee
Type? t3 = Type.GetType("System.Text.StringBuilder");   // by name (needs assembly-qualified name outside CoreLib)

Console.WriteLine(t2.Name);                    // Manager
Console.WriteLine(t2.FullName);                // Manager (namespace prefix if it has one)
Console.WriteLine(t2.BaseType?.Name);          // Employee
Console.WriteLine(t2.IsClass);                 // True
Console.WriteLine(t1.IsAssignableFrom(t2));    // True — a Manager can be used as an Employee
Console.WriteLine(e is Employee);              // True — prefer `is` when you know the type at compile time
""", "TypeBasics.cs")}

<h3>2. Properties: reading and writing by name</h3>
{C(r"""
using System.Reflection;

static void Dump(object obj)
{
    Type type = obj.GetType();
    Console.WriteLine($"--- {type.Name} ---");
    foreach (PropertyInfo p in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
        Console.WriteLine($"{p.Name,-14} {p.PropertyType.Name,-8} = {p.GetValue(obj)}");
}

var priya = new Manager { Id = 104, Name = "Priya Sharma", City = "Pune", MonthlySalary = 185_000m, TeamSize = 6 };
Dump(priya);
// --- Manager ---
// TeamSize       Int32    = 6
// Id             Int32    = 104
// Name           String   = Priya Sharma
// City           String   = Pune
// MonthlySalary  Decimal  = 185000

// Set a property from a column name — the heart of every CSV/DB mapper
PropertyInfo? city = typeof(Employee).GetProperty("City");
city?.SetValue(priya, "Bengaluru");
Console.WriteLine(priya.City);                // Bengaluru

// A tiny generic CSV row mapper
static T MapRow<T>(string[] headers, string[] values) where T : new()
{
    var item = new T();
    for (int i = 0; i < headers.Length; i++)
    {
        PropertyInfo? prop = typeof(T).GetProperty(headers[i], BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
        if (prop is null || !prop.CanWrite) continue;
        object converted = Convert.ChangeType(values[i], prop.PropertyType, System.Globalization.CultureInfo.InvariantCulture);
        prop.SetValue(item, converted);
    }
    return item;
}

var row = MapRow<Employee>(["id", "name", "city", "monthlysalary"], ["201", "Arjun Nair", "Kochi", "72000"]);
Console.WriteLine($"{row.Name} from {row.City} earns {row.MonthlySalary:N0}");   // Arjun Nair from Kochi earns 72,000
""", "Properties.cs")}
<p class="muted">The order of <code>GetProperties()</code> results is not guaranteed by the documentation; in practice derived-class properties come first. Never rely on it.</p>

<h3>3. Creating instances and invoking methods</h3>
{C(r"""
using System.Reflection;

// Create by Type
object emp = Activator.CreateInstance(typeof(Employee))!;          // needs a parameterless constructor
var sb = (System.Text.StringBuilder)Activator.CreateInstance(typeof(System.Text.StringBuilder), "INV-")!;   // with args

// Invoke a public method by name
MethodInfo greet = typeof(Employee).GetMethod(nameof(Employee.Greet))!;
var ravi = new Employee { Name = "Ravi" };
Console.WriteLine(greet.Invoke(ravi, ["Namaste"]));               // Namaste, Ravi

// Private members are reachable too (tests/tools only!)
MethodInfo masked = typeof(Employee).GetMethod("MaskedPan", BindingFlags.NonPublic | BindingFlags.Instance)!;
typeof(Employee).GetField("_pan", BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(ravi, "ABCDE1234F");
Console.WriteLine(masked.Invoke(ravi, null));                      // XXXXX1234F
""", "Invoke.cs")}
<h4>A plugin-style discovery: find every implementation of an interface</h4>
{C(r"""
using System.Reflection;

foreach (var rule in DiscountRules.LoadAll())
    Console.WriteLine($"{rule.Name}: {rule.Apply(10_000m):N2}");
// Diwali 10%: 9,000.00
// Senior 5%: 9,500.00

public interface IDiscountRule
{
    string Name { get; }
    decimal Apply(decimal amount);
}
public sealed class DiwaliDiscount : IDiscountRule { public string Name => "Diwali 10%"; public decimal Apply(decimal a) => a * 0.90m; }
public sealed class SeniorCitizenDiscount : IDiscountRule { public string Name => "Senior 5%"; public decimal Apply(decimal a) => a * 0.95m; }

public static class DiscountRules
{
    public static IReadOnlyList<IDiscountRule> LoadAll() =>
        Assembly.GetExecutingAssembly()
                .GetTypes()
                .Where(t => t is { IsClass: true, IsAbstract: false } && typeof(IDiscountRule).IsAssignableFrom(t))
                .Select(t => (IDiscountRule)Activator.CreateInstance(t)!)
                .ToList();
}

""", "DiscountRules.cs")}
<p>This is exactly what DI containers do when you call something like <code>AddClassesFromAssembly</code>, and what xUnit does to find <code>[Fact]</code> methods.</p>

<h3>4. Attributes: built-in and custom</h3>
{table(["Attribute","Read by","Effect"],[
["<code>[Obsolete(\"Use V2\")]</code>","Compiler","Warning (or error) where it's used"],
["<code>[Flags]</code>","Enum.ToString","Prints combined values as \"Read, Write\""],
["<code>[JsonPropertyName(\"emp_id\")]</code>","System.Text.Json","Renames the JSON property (Week 6)"],
["<code>[CallerMemberName]</code>","Compiler","Fills in the calling method's name"],
["<code>[Fact]</code>","xUnit (reflection)","Marks a test method (Week 10)"],
["<code>[Required]</code>, <code>[Range]</code> (DataAnnotations)","ASP.NET Core model validation","Validates request models (Week 17)"],
["<code>[MethodImpl(NoInlining)]</code>","JIT","Prevents inlining (used in Saturday's lab)"]])}
{C(r"""
namespace Mini.Validation;

[AttributeUsage(AttributeTargets.Property, AllowMultiple = false, Inherited = true)]
public abstract class ValidationAttribute : Attribute
{
    public string? Message { get; init; }                     // named argument: [Required(Message = "...")]
    public abstract bool IsValid(object? value);
    public virtual string FormatError(string property) => Message ?? $"{property} is invalid";
}

public sealed class RequiredAttribute : ValidationAttribute
{
    public override bool IsValid(object? value) => value switch
    {
        null => false,
        string s => !string.IsNullOrWhiteSpace(s),
        _ => true
    };
    public override string FormatError(string property) => Message ?? $"{property} is required";
}

public sealed class RangeAttribute(double min, double max) : ValidationAttribute   // ctor args: constants only
{
    public double Min { get; } = min;
    public double Max { get; } = max;

    public override bool IsValid(object? value) =>
        value is null || (Convert.ToDouble(value) is var d && d >= Min && d <= Max);   // null is Required's job
    public override string FormatError(string property) => Message ?? $"{property} must be between {Min} and {Max}";
}

public sealed class MaxLengthAttribute(int length) : ValidationAttribute
{
    public int Length { get; } = length;
    public override bool IsValid(object? value) => value is not string s || s.Length <= Length;
    public override string FormatError(string property) => Message ?? $"{property} must be at most {Length} characters";
}
""", "Mini.Validation/Attributes.cs")}
{warn("You can't write <code>[Range(10_000m, 5_00_000m)]</code>: decimal isn't a valid attribute argument type. That's why RangeAttribute here (and the real DataAnnotations one) takes double, or takes a Type plus strings.", "Gotcha")}

<h3>5. Reading attributes: a tiny validation framework</h3>
{C(r"""
using System.Collections.Concurrent;
using System.Reflection;

namespace Mini.Validation;

public static class Validator
{
    // Reflection lookups are slow; do them once per type and cache the result
    private static readonly ConcurrentDictionary<Type, (PropertyInfo Prop, ValidationAttribute[] Rules)[]> Cache = new();

    public static IReadOnlyList<string> Validate(object model)
    {
        ArgumentNullException.ThrowIfNull(model);
        var rules = Cache.GetOrAdd(model.GetType(), static type =>
            type.GetProperties(BindingFlags.Public | BindingFlags.Instance)
                .Select(p => (p, p.GetCustomAttributes<ValidationAttribute>(inherit: true).ToArray()))
                .Where(x => x.Item2.Length > 0)
                .ToArray());

        var errors = new List<string>();
        foreach (var (prop, attributes) in rules)
        {
            object? value = prop.GetValue(model);
            foreach (var attribute in attributes)
                if (!attribute.IsValid(value))
                    errors.Add(attribute.FormatError(prop.Name));
        }
        return errors;
    }
}
""", "Mini.Validation/Validator.cs")}
{C(r"""
using Mini.Validation;

var form = new JoiningForm { Name = " ", Age = 17, City = "Visakhapatnam-Vizag-Andhra Pradesh", MonthlySalary = 9_000m };
foreach (string error in Validator.Validate(form))
    Console.WriteLine($"✗ {error}");
// ✗ Name is required
// ✗ Age must be between 18 and 60
// ✗ City must be at most 20 characters
// ✗ Salary must be at least ₹10,000

var ok = new JoiningForm { Name = "Meena Iyer", Age = 29, City = "Chennai", MonthlySalary = 65_000m };
Console.WriteLine(Validator.Validate(ok).Count);   // 0

public class JoiningForm
{
    [Required] public string Name { get; set; } = "";
    [Range(18, 60)] public int Age { get; set; }
    [Required, MaxLength(20)] public string City { get; set; } = "";
    [Range(10_000, 10_00_000, Message = "Salary must be at least ₹10,000")] public decimal MonthlySalary { get; set; }
}
""", "Program.cs")}
<p>Built-in equivalent you'll use with ASP.NET Core: <code>System.ComponentModel.DataAnnotations</code> has <code>[Required]</code>, <code>[Range]</code>, <code>[MaxLength]</code>, <code>[EmailAddress]</code>, and <code>Validator.TryValidateObject</code> reads them the same way.</p>

<h3>6. The cost of reflection, and the alternatives</h3>
{C(r"""
using System.Reflection;

var emp = new Employee { MonthlySalary = 85_000m };
PropertyInfo prop = typeof(Employee).GetProperty(nameof(Employee.MonthlySalary))!;
Func<Employee, decimal> getter = prop.GetMethod!.CreateDelegate<Func<Employee, decimal>>();   // .NET 5+

decimal a = emp.MonthlySalary;                     // direct
decimal b = (decimal)prop.GetValue(emp)!;          // reflection: boxes the decimal, checks, dispatches
decimal c = getter(emp);                           // cached delegate: near-direct speed

// Approximate, from one 2-core cloud VM, .NET 8, 10 million calls each (per call; varies a lot by machine):
// direct ~5 ns | cached delegate ~10-15 ns | PropertyInfo.GetValue ~90-110 ns | GetProperty("...") lookup + GetValue ~150+ ns
""", "ReflectionCost.cs")}
{table(["Approach","Speed","AOT / trimming friendly","Use for"],[
["Direct code","Fastest","Yes","Everything you know at compile time"],
["Reflection, cached PropertyInfo/MethodInfo","Often 10x+ slower per call","Needs annotations","Tools, startup-time scanning, rare calls"],
["Reflection, lookup every time","Slowest","No","Never in a loop"],
["Compiled delegates / expression trees","Close to direct after setup","Partially","Mappers and serializers built at startup"],
["Source generators","Same as hand-written","Yes","JSON, regex, logging, mapping in modern .NET"]])}
{C(r"""
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

bool valid = Patterns.PinCode().IsMatch("560001");                               // True
string json = JsonSerializer.Serialize(new Employee { Name = "Asha" }, AppJsonContext.Default.Employee);
Console.WriteLine($"{valid} {json}");   // True {"Id":0,"Name":"Asha","City":"","MonthlySalary":0}

public static partial class Patterns
{
    [GeneratedRegex(@"^[1-9][0-9]{5}$")]          // .NET 7+: regex code generated at build time
    public static partial Regex PinCode();
}

[JsonSerializable(typeof(Employee))]               // System.Text.Json source generation: no runtime reflection
internal partial class AppJsonContext : JsonSerializerContext { }

""", "SourceGenerators.cs")}
''',
["Calling <code>GetProperty</code>/<code>GetMethod</code> inside a loop instead of caching the results.",
"Using <code>GetType()</code> when you meant <code>typeof</code> (or vice versa) and getting the base vs derived type wrong.",
"Forgetting <code>BindingFlags.Instance</code> (or Static) together with Public/NonPublic, and getting nothing back.",
"Trying to pass decimal, DateTime or <code>new</code> objects as attribute arguments.",
"Reaching into private fields of your own classes with reflection instead of fixing the design."],
("40 min", ["Write <code>string ToCsvLine(object obj)</code> that writes all public readable properties in declaration-independent but stable order (sort by name). Cache the PropertyInfo[] per type.",
"Add <code>[Pin]</code> (6 digits, first not 0) and <code>[Email]</code> attributes to the Mini.Validation framework and validate a <code>CustomerSignup</code> class.",
"Benchmark <code>PropertyInfo.GetValue</code> vs a cached delegate vs a direct property read for 1 million calls with Stopwatch, in Release."]),
[("What's the difference between typeof(X) and x.GetType()?","typeof is resolved at compile time for a named type. GetType() returns the actual runtime type of an instance, which may be a derived class."),
("Do attributes do anything on their own?","No. They're metadata; they only have an effect when the compiler, the runtime, a framework or your code reads them via reflection or a source generator."),
("Why cache PropertyInfo objects?","Looking members up by name is the most expensive part of reflection; caching per type leaves only the (cheaper) GetValue/SetValue cost.")],
[("Basic","What is reflection and where is it used?","The ability to inspect metadata and work with types and members at runtime: list properties, read/write values, create instances, invoke methods, read attributes. Used by serializers, ORMs (EF Core), DI containers, model binding and validation, test frameworks and plugin systems."),
("Basic","What are attributes and how do you create a custom one?","Declarative metadata attached to code elements. Create a class deriving from System.Attribute (name ending in Attribute), mark it with [AttributeUsage] to control targets, AllowMultiple and Inherited, and read it with GetCustomAttribute(s)."),
("Basic","How do you create an object when you only have its Type?","Activator.CreateInstance(type) for a parameterless constructor, or with an object[] of arguments; or get a ConstructorInfo with type.GetConstructor(...) and Invoke it. Generic code with a new() constraint can simply call new T()."),
("Intermediate","Why is reflection slow and how do you make it faster?","Member lookups search metadata by string, and Invoke/GetValue box arguments and results, check types and access, and can't be inlined. Cache MemberInfo objects, convert hot paths into strongly typed delegates (CreateDelegate) or compiled expression trees, or move the work to compile time with source generators."),
("Intermediate","How do reflection and Native AOT/trimming interact?","The trimmer removes code it can't see being used. Members accessed only by string names via reflection may be removed, causing runtime failures. You must annotate with [DynamicallyAccessedMembers], avoid dynamic loading and Reflection.Emit, and prefer source generators (e.g. System.Text.Json's JsonSerializerContext)."),
("Intermediate","What are source generators?","Roslyn components that run during compilation, inspect your code (often attributes) and add new C# source. They replace runtime reflection with ordinary generated code: faster startup, no reflection cost, and AOT-safe. Examples: [GeneratedRegex], System.Text.Json source generation, [LoggerMessage].")])

# ================= DAY 5 =================
d5 = day(5, "FRI", "Async and GC pitfalls, memory leaks and diagnostics",
"Recognise the async and memory mistakes that cause crashes, hangs and leaks in real systems, fix them, and know which tool to reach for when production misbehaves.",
[("async void","An async method that returns nothing awaitable. Exceptions go straight to the SynchronizationContext and usually crash the process."),
("Sync-over-async","Blocking on async code with <code>.Result</code>, <code>.Wait()</code> or <code>GetAwaiter().GetResult()</code>."),
("SynchronizationContext","Decides where an await continues: the UI thread in WinForms/WPF, the request context in legacy ASP.NET. ASP.NET Core and console apps have none."),
("ConfigureAwait(false)","Tells an await not to resume on the captured context; any thread-pool thread will do."),
("Deadlock","Two parties each waiting for the other forever, e.g. a blocked UI thread waiting for a continuation that needs the UI thread."),
("Thread-pool starvation","All pool threads are blocked waiting, so queued work (including the continuations they're waiting for) can't run; latency explodes."),
("Fire-and-forget","Starting a task without awaiting or observing it. Its exceptions are lost and its lifetime is unmanaged."),
("Managed memory leak","Objects that are no longer needed but are still reachable from a root, so the GC can't free them."),
("Event leak","A long-lived publisher's event holds a reference to a short-lived subscriber's handler, keeping the subscriber alive."),
("WeakReference","A reference that doesn't keep its target alive; used to test whether an object was collected."),
("dotnet-counters","CLI tool showing live runtime metrics: GC heap size, GC counts, allocation rate, thread-pool queue, exceptions."),
("dotnet-dump","CLI tool to capture and analyse a process memory dump: which objects exist and what roots them."),
("dotnet-gcdump","Lighter dump of just the GC heap, viewable in Visual Studio or PerfView."),
("dotnet-trace","CLI tool that records an event trace (CPU samples, GC events, allocations) for later analysis.")],
["Use async void only for event handlers, and wrap their bodies in try/catch.",
"Async all the way: if you call an async method, your method should be async and await it.",
"In library code, <code>ConfigureAwait(false)</code> avoids capturing a context you don't need.",
"A memory leak in .NET is always \"something still references it\". Find the root.",
"Classic roots of leaks: events, static collections, caches without limits, timers, closures.",
"Watch a counter first (is the heap growing?), then take a dump to see what and why."],
f'''
<h3>1. async void</h3>
{C(r"""
// ❌ async void: the caller can't await it or catch its exceptions
public async void SendInvoiceEmail(int invoiceId)
{
    await Task.Delay(100);
    throw new InvalidOperationException($"SMTP down for invoice {invoiceId}");   // crashes the process
}

try
{
    SendInvoiceEmail(42);              // returns at the first await; the exception happens later
}
catch (Exception) { /* never reached */ }

// ✓ async Task: awaitable and catchable
public async Task SendInvoiceEmailAsync(int invoiceId)
{
    await Task.Delay(100);
    throw new InvalidOperationException($"SMTP down for invoice {invoiceId}");
}
try { await SendInvoiceEmailAsync(42); }
catch (InvalidOperationException ex) { Console.WriteLine($"Logged: {ex.Message}"); }

// The one valid use: event handlers (their signature must return void)
private async void SaveButton_Click(object? sender, EventArgs e)
{
    try { await SaveAsync(); }
    catch (Exception ex) { ShowError(ex.Message); }   // never let it escape
}
""", "AsyncVoid.cs (fragment)")}

<h3>2. Sync-over-async deadlocks</h3>
<p>In a WinForms/WPF app (or classic ASP.NET on .NET Framework), awaits resume on the captured context, which only has one thread. Block that thread and the continuation can never run:</p>
<ol>
<li>The UI thread calls <code>LoadCustomerAsync().Result</code> and blocks, waiting for the task.</li>
<li>Inside, <code>await httpClient.GetStringAsync(...)</code> completes on an I/O thread.</li>
<li>The rest of LoadCustomerAsync must run on the UI thread (context captured), so it's posted there.</li>
<li>The UI thread is blocked in step 1 forever. Deadlock.</li>
</ol>
{C(r"""
// WinForms button handler — ❌ freezes forever
private void LoadButton_Click(object sender, EventArgs e)
{
    string name = LoadCustomerAsync(101).Result;     // blocks the UI thread
    nameLabel.Text = name;
}

private async Task<string> LoadCustomerAsync(int id)
{
    string json = await _http.GetStringAsync($"https://api.example.com/customers/{id}");
    return ParseName(json);                          // needs the UI thread to run → never gets it
}

// ✓ Fix 1 (the real fix): async all the way
private async void LoadButton_Click2(object sender, EventArgs e)
{
    try { nameLabel.Text = await LoadCustomerAsync(101); }
    catch (HttpRequestException ex) { MessageBox.Show(ex.Message); }
}

// ✓ Fix 2 (library code): don't capture the context you don't need
public async Task<string> LoadCustomerLibAsync(int id)
{
    string json = await _http.GetStringAsync($"https://api.example.com/customers/{id}").ConfigureAwait(false);
    return ParseName(json);                          // runs on a thread-pool thread
}
""", "Deadlock.cs (WinForms fragment)")}
{table(["Environment","SynchronizationContext","Does .Result deadlock?","Is .Result still bad?"],[
["WinForms / WPF / MAUI UI thread","Single UI thread","Yes","Yes"],
["ASP.NET on .NET Framework","Request context","Yes","Yes"],
["ASP.NET Core","None","No","Yes: blocks a pool thread; under load causes thread-pool starvation"],
["Console app","None","No","Yes, though harmless in a simple Main"]])}
{tip("If you truly can't make a caller async (e.g. a legacy interface), prefer <code>GetAwaiter().GetResult()</code> over <code>.Result</code>: it throws the original exception instead of an AggregateException. It still blocks.")}

<h3>3. Fire-and-forget</h3>
{C(r"""
// ❌ In an ASP.NET Core controller
[HttpPost("orders")]
public IActionResult PlaceOrder(OrderDto dto)
{
    _ = _email.SendConfirmationAsync(dto.Email);  // exception lost; and if it uses the scoped DbContext,
    return Accepted();                            // that context is disposed when the request ends
}

// ✓ Option 1: just await it (most of the time this is fine)
await _email.SendConfirmationAsync(dto.Email);

// ✓ Option 2: hand it to a background worker that owns its lifetime and logs failures
//   (Channel<T> + BackgroundService from Week 7)
await _emailQueue.Writer.WriteAsync(new EmailJob(dto.Email, dto.OrderId));
""", "FireAndForget.cs (fragment)")}
{C(r"""
// If you really must fire and forget, at least observe and log the failure
public static class TaskExtensions
{
    public static void Forget(this Task task, ILogger logger) =>
        task.ContinueWith(t => logger.LogError(t.Exception, "Background task failed"),
                          TaskContinuationOptions.OnlyOnFaulted);
}
""", "TaskExtensions.cs")}

<h3>4. Memory leaks in managed code</h3>
{table(["Leak source","How it holds memory","Fix"],[
["Events on a long-lived publisher","Publisher's delegate list references each subscriber","Unsubscribe in Dispose; weak events; scope the publisher"],
["Static collections / caches","Statics are GC roots for the life of the process","Bounded cache with expiry (<code>MemoryCache</code> with SizeLimit), or no static state"],
["Closures","A lambda keeps every captured variable (and the whole closure object) alive","Capture only small values you need; copy to a local first"],
["Timers","The runtime's timer queue references the callback, which references your object","Dispose the timer; prefer PeriodicTimer with a CancellationToken"],
["Undisposed streams / handles","OS handles and buffers held until a finalizer runs, maybe never; files stay locked","<code>using</code> / <code>await using</code>"],
["Long-lived async work","A never-completing task holds its state machine and everything it references","Cancellation tokens and timeouts"]])}
<h4>Static collection</h4>
{C(r"""
// ❌ grows forever: every request adds, nothing removes
public static class QuoteCache
{
    public static readonly Dictionary<string, byte[]> PdfsByQuoteId = new();
}

// ✓ bounded and expiring (Microsoft.Extensions.Caching.Memory)
var cache = new MemoryCache(new MemoryCacheOptions { SizeLimit = 200 });
cache.Set("Q-1001", pdfBytes, new MemoryCacheEntryOptions
{
    Size = 1,                                        // each entry counts as 1 towards SizeLimit
    SlidingExpiration = TimeSpan.FromMinutes(10)
});
""", "StaticLeak.cs (fragment)")}
<h4>Closure capturing a large object</h4>
{C(r"""
var auditLog = new List<Func<string>>();        // long-lived, e.g. a singleton's field

void GenerateStatement(string path)
{
    byte[] pdf = File.ReadAllBytes(path);        // say 5 MB
    string fileName = Path.GetFileName(path);

    // ❌ the lambda captures `pdf`, so 5 MB stays alive as long as auditLog holds this lambda
    auditLog.Add(() => $"Generated {fileName} ({pdf.Length:N0} bytes)");

    // ✓ capture only what you need
    int size = pdf.Length;
    auditLog.Add(() => $"Generated {fileName} ({size:N0} bytes)");
    // ⚠ but if ANY lambda in this method captures `pdf`, all lambdas share one closure object that holds it
}
""", "ClosureLeak.cs (fragment)")}
<h4>Timers</h4>
{C(r"""
// ❌ the timer queue roots the callback → `this` → this object never dies and keeps polling
public sealed class GoldRatePoller
{
    private readonly Timer _timer;
    private readonly byte[] _history = new byte[1_000_000];
    public GoldRatePoller() => _timer = new Timer(_ => Poll(), null, TimeSpan.Zero, TimeSpan.FromSeconds(5));
    private void Poll() => _history[0]++;
}

// ✓ disposable, and modern: PeriodicTimer (.NET 6+) with cancellation
public sealed class GoldRateWorker(ILogger<GoldRateWorker> logger) : IAsyncDisposable
{
    private readonly CancellationTokenSource _cts = new();
    private Task? _loop;

    public void Start() => _loop = RunAsync(_cts.Token);

    private async Task RunAsync(CancellationToken ct)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(5));
        try
        {
            while (await timer.WaitForNextTickAsync(ct))
                logger.LogInformation("Polling gold rate at {Time}", DateTime.Now);
        }
        catch (OperationCanceledException) { /* stopping */ }
    }

    public async ValueTask DisposeAsync()
    {
        _cts.Cancel();
        if (_loop is not null) await _loop;
        _cts.Dispose();
    }
}
""", "Timers.cs (fragment)")}
{warn("The opposite timer bug also exists: a <code>System.Threading.Timer</code> stored only in a local variable, whose callback doesn't reference it, can be garbage-collected and silently stop firing. Keep a reference and dispose it when done.", "Also")}
<h4>Unclosed streams</h4>
{C(r"""
// ❌ handle stays open until a finalizer runs (maybe never); the file stays locked on Windows
var writer = new StreamWriter("gst-report.csv");
writer.WriteLine("Invoice,Amount,GST");
// forgot writer.Dispose() → data may not even be flushed

// ✓
using (var w = new StreamWriter("gst-report.csv"))
    w.WriteLine("Invoice,Amount,GST");

await using var stream = File.Create("gst-report.json");   // async disposal for async streams
""", "Streams.cs (fragment)")}

<h3>5. Diagnosing: counters, dumps, Visual Studio</h3>
{C(r"""
# Install once
dotnet tool install --global dotnet-counters
dotnet tool install --global dotnet-dump
dotnet tool install --global dotnet-gcdump
dotnet tool install --global dotnet-trace

# 1. Find the process and watch live metrics
dotnet-counters ps
dotnet-counters monitor -n Internals.Lab --counters System.Runtime
#   GC Heap Size (MB)                 ← keeps climbing and never drops after GCs? leak
#   Gen 0/1/2 GC Count                ← many gen 2 GCs? LOH churn or mid-life objects
#   Allocation Rate (B / 1 sec)       ← how much garbage you create
#   ThreadPool Queue Length / Thread Count  ← growing queue + many threads = starvation (sync-over-async)
#   Exception Count, % Time in GC

# 2. Capture what's in memory
dotnet-dump collect -n Internals.Lab               # full dump: heap + threads + stacks
dotnet-gcdump collect -n Internals.Lab             # GC heap only; open the .gcdump in Visual Studio

# 3. Analyse a full dump
dotnet-dump analyze core_20261110_101500
> dumpheap -stat                                   # object counts and sizes by type, biggest at the bottom
> dumpheap -type LeakyQuoteScreen                  # every instance with its address
> gcroot 00007f3a2c0a1b20                          # the chain of references keeping it alive
> clrthreads                                       # managed threads
> pe                                               # print the current exception

# 4. Trace CPU or allocations over time
dotnet-trace collect -n Internals.Lab --profile gc-verbose
""", lang="bash")}
{table(["Symptom","First look at","Then","Usual cause"],[
["Memory grows until OOM / container restart","dotnet-counters: GC heap size","Two gcdumps a few minutes apart, compare; gcroot on the growing type","Events, static caches, timers"],
["Latency spikes, CPU fine, requests queue","ThreadPool queue length and thread count","dotnet-dump: <code>clrstack -all</code> / <code>parallelstacks</code> shows threads blocked in .Result/.Wait","Sync-over-async"],
["High CPU in GC, many gen 2 collections","% Time in GC, Gen 2 count, LOH size","dotnet-trace with gc-verbose; allocation profiler","Large buffers per request, too many allocations"],
["App hangs completely (desktop)","Attach VS, Debug → Break All, Parallel Stacks","Look for the UI thread waiting on a Task","Deadlock from .Result on the UI thread"]])}
<p><b>Visual Studio (awareness):</b> the <b>Diagnostic Tools</b> window shows memory and CPU while debugging and lets you take heap snapshots and diff them (\"+1,250 QuoteScreen objects since snapshot 1\"). <b>Debug → Performance Profiler</b> (Alt+F2) has .NET Object Allocation Tracking, CPU Usage and Memory Usage tools that work on Release builds. Rider and PerfView offer the same ideas.</p>
''',
["Writing <code>async void</code> methods other than event handlers.",
"Calling <code>.Result</code> or <code>.Wait()</code> on tasks in UI code or in ASP.NET Core request paths.",
"<code>_ = SomethingAsync()</code> in a request handler using scoped services like DbContext.",
"Subscribing to a long-lived object's event from a short-lived object and never unsubscribing.",
"Restarting the app when memory grows instead of taking two dumps and finding the root."],
("40 min", ["Write a console app with a static <code>List&lt;byte[]&gt;</code> that adds 1 MB every 100 ms. Run <code>dotnet-counters monitor</code> against it and watch GC Heap Size and Gen 2 count.",
"Take a <code>dotnet-dump</code> of that app, run <code>dumpheap -stat</code> and <code>gcroot</code> on one of the arrays, and write down the root chain you see.",
"Rewrite a method that uses <code>.Result</code> on three HTTP calls (use <code>Task.Delay</code> to fake them) to be async all the way, running the three in parallel with <code>Task.WhenAll</code>."]),
[("Why is async void dangerous?","The caller can't await it, so it can't know when it finishes, and exceptions can't be caught by the caller; they're raised on the SynchronizationContext and typically crash the process."),
("Why doesn't .Result deadlock in ASP.NET Core?","ASP.NET Core has no SynchronizationContext, so continuations run on any thread-pool thread. It still blocks a thread and can cause thread-pool starvation under load."),
("What tool shows you why an object is still alive?","A memory dump analysed with dotnet-dump (gcroot), or a heap snapshot in Visual Studio / dotnet-gcdump, which shows the reference path from a GC root.")],
[("Basic","When is async void acceptable?","Only for event handlers, whose delegate signature requires void. Everything else should return Task or ValueTask. Inside such handlers, catch exceptions yourself because nothing else can."),
("Basic","What causes the classic .Result deadlock?","Blocking a thread that is also the only thread allowed to run the awaited method's continuation — the UI thread or legacy ASP.NET request context. The task can't complete without that thread, and the thread won't be released until the task completes."),
("Basic","Can a .NET application have memory leaks if it has a garbage collector?","Yes. The GC only frees unreachable objects. If something no longer needed is still referenced — from a static collection, an event, a timer callback, a closure or a cache — it can't be collected and memory grows."),
("Intermediate","What does ConfigureAwait(false) do and when should you use it?","It tells the await not to resume on the captured SynchronizationContext or TaskScheduler. Use it in general-purpose library code that doesn't touch UI or HttpContext, to avoid deadlocks for callers that block and to save the context switch. In ASP.NET Core app code it makes no practical difference because there's no context."),
("Intermediate","How would you investigate a memory leak in a production .NET service?","Confirm with dotnet-counters (or metrics) that the GC heap grows across gen 2 collections. Take two gcdumps or full dumps some minutes apart and compare type counts to find what grows. Use gcroot (dotnet-dump) or VS's paths-to-root to see what holds those objects. Fix the root: unsubscribe events, bound caches, dispose timers. Verify with counters after the fix."),
("Intermediate","What is thread-pool starvation and how do you spot it?","When pool threads are blocked (often by sync-over-async), new work and continuations wait in the queue while the pool injects threads slowly. Symptoms: high latency with low CPU, a growing ThreadPool Queue Length and Thread Count in dotnet-counters, and dumps showing many threads blocked in Wait/Result. Fix by making the code async end to end.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Internals lab: measure GC, Span and leaks, then write it up",
"Build a small console lab that runs six experiments, predict each result before you run it, record what actually happens, and turn your notes into a blog post explaining GC and async in your own words. Budget: about 4 hours.",
[("Experiment","A small, repeatable piece of code with a question, a prediction and a measured result."),
("Lab notebook","A markdown file the app appends each run's prediction and output to."),
("Warm-up","Running code once before measuring so JIT compilation and static initialisation aren't counted."),
("Benchmark","A careful, repeated measurement; BenchmarkDotNet automates warm-up, statistics and allocation counting.")],
["Predict first, then run. A wrong prediction is the most valuable result of the day.",
"Always run in Release: <code>dotnet run -c Release</code>.",
"Allocation numbers are exact and portable; timings depend on your machine — compare ratios, not milliseconds.",
"<code>GC.Collect()</code> appears in this lab on purpose, to make the GC observable. It still doesn't belong in app code.",
"The blog post is the real deliverable: explaining something is how you find out whether you understand it."],
f'''
<h3>Plan for today (≈4 hours)</h3>
{table(["Time","Activity"],[
["20 min","Scaffold the solution, add IExperiment, Measure and LabNotebook"],
["90 min","Type in the six experiments one at a time; predict, run, record each"],
["20 min","Optional: BenchmarkDotNet comparison of the two parsers"],
["15 min","Fill in the results table below with your own numbers"],
["75 min","Write the blog post from the outline at the end"]])}

<h3>Requirements</h3>
<ul>
<li>A class library <code>Internals.Lab.Core</code> containing the experiments, and a console app <code>Internals.Lab</code> that runs them.</li>
<li>Every experiment implements <code>IExperiment</code>: an id, a title, a question to predict, and <code>Run(TextWriter)</code>.</li>
<li>A <code>Measure</code> helper reports bytes allocated (<code>GC.GetAllocatedBytesForCurrentThread</code>) and elapsed time, with warm-up.</li>
<li>Experiments: (1) what allocates, (2) generation promotion, (3) LOH threshold and ArrayPool, (4) Split/Substring vs Span parsing, (5) event leak and fix, (6) sync-over-async deadlock and ConfigureAwait(false).</li>
<li>Interactive menu, plus a non-interactive mode: <code>dotnet run -c Release -- all</code> or <code>-- span leak</code>.</li>
<li>Each run appends your prediction and the output to <code>lab-notebook.md</code>.</li>
</ul>

<h3>Scaffold</h3>
{C(r"""
mkdir InternalsLab && cd InternalsLab
dotnet new sln -n InternalsLab
dotnet new classlib -n Internals.Lab.Core
dotnet new console  -n Internals.Lab
dotnet sln add Internals.Lab.Core Internals.Lab
dotnet add Internals.Lab reference Internals.Lab.Core
rm Internals.Lab.Core/Class1.cs
mkdir Internals.Lab.Core/Experiments
""", lang="bash")}
{C(r"""
InternalsLab/
├─ InternalsLab.sln
├─ Internals.Lab.Core/
│  ├─ IExperiment.cs
│  ├─ Measure.cs
│  └─ Experiments/
│     ├─ AllocationExperiment.cs
│     ├─ GenerationExperiment.cs
│     ├─ LohExperiment.cs
│     ├─ SpanParsingExperiment.cs
│     ├─ EventLeakExperiment.cs
│     └─ DeadlockExperiment.cs
├─ Internals.Lab/
│  ├─ LabNotebook.cs
│  └─ Program.cs
└─ Internals.Lab.Bench/          (optional, step 9)
   └─ Program.cs
""", lang="text")}

<h3>Step 1 — The experiment contract</h3>
{C(r"""
namespace Internals.Lab.Core;

public interface IExperiment
{
    string Id { get; }          // short key used on the command line, e.g. "gen"
    string Title { get; }
    string Question { get; }    // what you should predict BEFORE running
    void Run(TextWriter output);
}
""", "Internals.Lab.Core/IExperiment.cs")}

<h3>Step 2 — Measuring allocations and time</h3>
{C(r"""
using System.Diagnostics;

namespace Internals.Lab.Core;

public readonly record struct Measurement<T>(T Result, long AllocatedBytes, TimeSpan Elapsed);

public static class Measure
{
    /// <summary>Runs the action once and reports bytes allocated on this thread and time taken.</summary>
    public static Measurement<T> Run<T>(Func<T> action)
    {
        long before = GC.GetAllocatedBytesForCurrentThread();
        long start = Stopwatch.GetTimestamp();             // a long, not a Stopwatch object: measuring must not allocate
        T result = action();
        TimeSpan elapsed = Stopwatch.GetElapsedTime(start); // .NET 7+
        long allocated = GC.GetAllocatedBytesForCurrentThread() - before;
        return new Measurement<T>(result, allocated, elapsed);
    }

    /// <summary>Warm up (JIT, static init), then measure the best of several runs.</summary>
    public static Measurement<T> Best<T>(Func<T> action, int runs = 5)
    {
        action();                                         // warm-up: not measured
        Measurement<T> best = Run(action);
        for (int i = 1; i < runs; i++)
        {
            var m = Run(action);
            if (m.Elapsed < best.Elapsed) best = m;
        }
        return best;
    }

    public static string Bytes(long bytes) => bytes switch
    {
        < 0 => "-" + Bytes(-bytes),
        < 1024 => $"{bytes} B",
        < 1024 * 1024 => $"{bytes / 1024.0:N1} KB",
        _ => $"{bytes / (1024.0 * 1024):N1} MB"
    };
}
""", "Internals.Lab.Core/Measure.cs")}
{tip("The first version of this helper used <code>Stopwatch.StartNew()</code>, and every \"zero-allocation\" case reported 40 bytes: the Stopwatch object itself. Measuring tools must not disturb what they measure.")}

<h3>Step 3 — Experiment 1: what allocates?</h3>
{C(r"""
using System.Collections;
using System.Text;

namespace Internals.Lab.Core.Experiments;

public sealed class AllocationExperiment : IExperiment
{
    public string Id => "alloc";
    public string Title => "1. What allocates?";
    public string Question => "Which of these allocate on the heap, and roughly how many bytes for 1,000 items?";

    private const int N = 1_000;

    public void Run(TextWriter output)
    {
        var cases = new (string Name, Func<int> Work)[]
        {
            ("int[] of 1,000",                  () => new int[N].Length),
            ("List<int> + 1,000 Add (no presize)", () => { var l = new List<int>(); for (int i = 0; i < N; i++) l.Add(i); return l.Count; }),
            ("List<int>(1,000) presized",        () => { var l = new List<int>(N); for (int i = 0; i < N; i++) l.Add(i); return l.Count; }),
            ("ArrayList + 1,000 Add (boxing)",   () => { var l = new ArrayList(N); for (int i = 0; i < N; i++) l.Add(i); return l.Count; }),
            ("string += 1,000 times",            () => { string s = ""; for (int i = 0; i < N; i++) s += "x"; return s.Length; }),
            ("StringBuilder 1,000 Append",       () => { var sb = new StringBuilder(); for (int i = 0; i < N; i++) sb.Append('x'); return sb.ToString().Length; }),
            ("1,000 record class Point",         () => { int sum = 0; for (int i = 0; i < N; i++) { var p = new PointClass(i, i); sum += p.X; } return sum; }),
            ("1,000 record struct Point",        () => { int sum = 0; for (int i = 0; i < N; i++) { var p = new PointStruct(i, i); sum += p.X; } return sum; }),
        };

        output.WriteLine($"{"Case",-38} {"Allocated",12}");
        foreach (var (name, work) in cases)
        {
            var m = Measure.Best(work);
            output.WriteLine($"{name,-38} {Measure.Bytes(m.AllocatedBytes),12}");
        }
    }

    private sealed record PointClass(int X, int Y);
    private readonly record struct PointStruct(int X, int Y);
}
""", "Internals.Lab.Core/Experiments/AllocationExperiment.cs")}

<h3>Step 4 — Experiment 2: generation promotion</h3>
{C(r"""
namespace Internals.Lab.Core.Experiments;

public sealed class GenerationExperiment : IExperiment
{
    public string Id => "gen";
    public string Title => "2. Watching an object get promoted";
    public string Question => "A new object starts in which generation? What happens after each GC it survives?";

    public void Run(TextWriter output)
    {
        var invoice = new Invoice("INV-2026-0042", 11_800m);
        output.WriteLine($"Just allocated:         gen {GC.GetGeneration(invoice)}");

        GC.Collect();                       // learning only: never do this in production code
        output.WriteLine($"Survived 1 collection:  gen {GC.GetGeneration(invoice)}");

        GC.Collect();
        output.WriteLine($"Survived 2 collections: gen {GC.GetGeneration(invoice)}");

        GC.Collect();
        output.WriteLine($"Survived 3 collections: gen {GC.GetGeneration(invoice)} (gen 2 is the oldest)");
        GC.KeepAlive(invoice);              // keep it reachable until here

        // Short-lived garbage mostly dies in gen 0 — cheap collections
        int g0 = GC.CollectionCount(0), g1 = GC.CollectionCount(1), g2 = GC.CollectionCount(2);
        long allocatedBefore = GC.GetTotalAllocatedBytes();
        long checksum = 0;
        for (int i = 0; i < 10_000_000; i++)
        {
            var temp = new Invoice($"INV-{i}", i);   // garbage immediately
            checksum += temp.Number.Length;
        }
        output.WriteLine();
        output.WriteLine($"After 10,000,000 short-lived invoices (checksum {checksum}):");
        output.WriteLine($"  allocated:        {Measure.Bytes(GC.GetTotalAllocatedBytes() - allocatedBefore)}");
        output.WriteLine($"  gen0 collections: {GC.CollectionCount(0) - g0}");
        output.WriteLine($"  gen1 collections: {GC.CollectionCount(1) - g1}");
        output.WriteLine($"  gen2 collections: {GC.CollectionCount(2) - g2}");
    }

    private sealed record Invoice(string Number, decimal Amount);
}
""", "Internals.Lab.Core/Experiments/GenerationExperiment.cs")}

<h3>Step 5 — Experiment 3: the LOH threshold</h3>
{C(r"""
using System.Buffers;

namespace Internals.Lab.Core.Experiments;

public sealed class LohExperiment : IExperiment
{
    public string Id => "loh";
    public string Title => "3. Finding the Large Object Heap threshold";
    public string Question => "At what array length does a byte[] land on the LOH (reported as gen 2 straight away)?";

    public void Run(TextWriter output)
    {
        int[] lengths = [1_000, 80_000, 84_975, 84_976, 85_000, 1_000_000];
        output.WriteLine($"{"byte[] length",14} {"Generation",11}  Heap");
        foreach (int length in lengths)
        {
            var buffer = new byte[length];
            int gen = GC.GetGeneration(buffer);
            output.WriteLine($"{length,14:N0} {gen,11}  {(gen == 2 ? "LOH" : "SOH")}");
        }
        output.WriteLine("(On 64-bit an array has a 24-byte header, so 84,976 + 24 = 85,000 bytes.)");

        // Cost: renting large buffers vs allocating them
        output.WriteLine();
        int g2Before = GC.CollectionCount(2);
        long sum = 0;
        for (int i = 0; i < 2_000; i++)
        {
            var report = new byte[200_000];          // new LOH object every time
            report[i % report.Length] = 1;
            sum += report.Length;
        }
        output.WriteLine($"new byte[200_000] x 2,000:       gen2 GCs = {GC.CollectionCount(2) - g2Before}");

        g2Before = GC.CollectionCount(2);
        for (int i = 0; i < 2_000; i++)
        {
            byte[] report = ArrayPool<byte>.Shared.Rent(200_000);   // reused, may be larger than asked
            try { report[i % 200_000] = 1; sum += report.Length; }
            finally { ArrayPool<byte>.Shared.Return(report); }
        }
        output.WriteLine($"ArrayPool.Rent(200_000) x 2,000: gen2 GCs = {GC.CollectionCount(2) - g2Before}");
        GC.KeepAlive(sum);
    }
}
""", "Internals.Lab.Core/Experiments/LohExperiment.cs")}

<h3>Step 6 — Experiment 4: Split/Substring vs Span</h3>
{C(r"""
using System.Globalization;

namespace Internals.Lab.Core.Experiments;

public sealed class SpanParsingExperiment : IExperiment
{
    public string Id => "span";
    public string Title => "4. Split/Substring vs ReadOnlySpan<char> parsing";
    public string Question => "How much less does span-based parsing allocate, and is it faster?";

    // Each line: orderId|pinCode|amount|state, e.g. ORD-100042|560001|1499.50|KA
    private readonly string[] _lines = BuildLines(100_000);

    public void Run(TextWriter output)
    {
        var classic = Measure.Best(() => TotalForPinPrefixClassic(_lines, "56"));
        var span    = Measure.Best(() => TotalForPinPrefixSpan(_lines, "56"));

        output.WriteLine($"{"Approach",-22} {"Total (INR)",16} {"Allocated",12} {"Time",10}");
        output.WriteLine($"{"Split + Substring",-22} {classic.Result,16:N2} {Measure.Bytes(classic.AllocatedBytes),12} {classic.Elapsed.TotalMilliseconds,8:N1}ms");
        output.WriteLine($"{"ReadOnlySpan<char>",-22} {span.Result,16:N2} {Measure.Bytes(span.AllocatedBytes),12} {span.Elapsed.TotalMilliseconds,8:N1}ms");
        output.WriteLine(classic.Result == span.Result ? "Totals match ✓" : "Totals DIFFER ✗ — check your parser");
    }

    public static decimal TotalForPinPrefixClassic(string[] lines, string pinPrefix)
    {
        decimal total = 0;
        foreach (string line in lines)
        {
            string[] parts = line.Split('|');                       // new array + 4 new strings per line
            if (parts[1].StartsWith(pinPrefix, StringComparison.Ordinal))
                total += decimal.Parse(parts[2], CultureInfo.InvariantCulture);
        }
        return total;
    }

    public static decimal TotalForPinPrefixSpan(string[] lines, string pinPrefix)
    {
        decimal total = 0;
        foreach (string line in lines)
        {
            ReadOnlySpan<char> rest = line;                         // a view, no copy
            rest = rest[(rest.IndexOf('|') + 1)..];                 // skip orderId
            int bar = rest.IndexOf('|');
            ReadOnlySpan<char> pin = rest[..bar];
            if (!pin.StartsWith(pinPrefix, StringComparison.Ordinal)) continue;

            rest = rest[(bar + 1)..];
            ReadOnlySpan<char> amount = rest[..rest.IndexOf('|')];
            total += decimal.Parse(amount, CultureInfo.InvariantCulture);   // span overload: no string
        }
        return total;
    }

    private static string[] BuildLines(int count)
    {
        string[] pins = ["560001", "400001", "110001", "600028", "560078", "700019"];
        string[] states = ["KA", "MH", "DL", "TN", "KA", "WB"];
        var rng = new Random(42);                                   // fixed seed: same data every run
        var lines = new string[count];
        for (int i = 0; i < count; i++)
        {
            int p = rng.Next(pins.Length);
            decimal amount = rng.Next(100, 500_000) / 100m;
            lines[i] = string.Create(CultureInfo.InvariantCulture, $"ORD-{100_000 + i}|{pins[p]}|{amount:F2}|{states[p]}");
        }
        return lines;
    }
}
""", "Internals.Lab.Core/Experiments/SpanParsingExperiment.cs")}
{warn("The span parser trusts the input format (it assumes four fields). In production, check every <code>IndexOf</code> result for -1 and use <code>decimal.TryParse</code>. Robustness first, then speed.", "Note")}

<h3>Step 7 — Experiment 5: an event leak and its fix</h3>
{C(r"""
using System.Runtime.CompilerServices;

namespace Internals.Lab.Core.Experiments;

public sealed class PriceTicker                       // long-lived publisher (think: a singleton service)
{
    public event EventHandler<decimal>? PriceChanged;
    public void Publish(decimal price) => PriceChanged?.Invoke(this, price);
    public int SubscriberCount => PriceChanged?.GetInvocationList().Length ?? 0;
}

public sealed class LeakyQuoteScreen                  // ❌ subscribes, never unsubscribes
{
    private readonly byte[] _chartCache = new byte[1_000_000];   // ~1 MB per screen
    public LeakyQuoteScreen(PriceTicker ticker) => ticker.PriceChanged += OnPrice;
    private void OnPrice(object? sender, decimal price) => _chartCache[0] = (byte)price;
}

public sealed class QuoteScreen : IDisposable         // ✓ unsubscribes in Dispose
{
    private readonly byte[] _chartCache = new byte[1_000_000];
    private readonly PriceTicker _ticker;
    public QuoteScreen(PriceTicker ticker) { _ticker = ticker; _ticker.PriceChanged += OnPrice; }
    private void OnPrice(object? sender, decimal price) => _chartCache[0] = (byte)price;
    public void Dispose() => _ticker.PriceChanged -= OnPrice;
}

public sealed class EventLeakExperiment : IExperiment
{
    public string Id => "leak";
    public string Title => "5. A memory leak through an event — and the fix";
    public string Question => "After we drop every reference to 50 screens and force a GC, how many are still alive?";

    private const int Screens = 50;

    public void Run(TextWriter output)
    {
        var ticker = new PriceTicker();

        long baseline = GC.GetTotalMemory(forceFullCollection: true);
        WeakReference[] leaky = OpenAndCloseLeakyScreens(ticker);
        ForceFullGc();
        output.WriteLine("Leaky screens (no unsubscribe):");
        output.WriteLine($"  still alive:   {leaky.Count(w => w.IsAlive)} of {Screens}");
        output.WriteLine($"  subscribers:   {ticker.SubscriberCount}");
        output.WriteLine($"  memory growth: {Measure.Bytes(GC.GetTotalMemory(true) - baseline)}");

        var ticker2 = new PriceTicker();
        baseline = GC.GetTotalMemory(forceFullCollection: true);
        WeakReference[] fixedOnes = OpenAndCloseDisposableScreens(ticker2);
        ForceFullGc();
        output.WriteLine("Disposable screens (unsubscribe in Dispose):");
        output.WriteLine($"  still alive:   {fixedOnes.Count(w => w.IsAlive)} of {Screens}");
        output.WriteLine($"  subscribers:   {ticker2.SubscriberCount}");
        output.WriteLine($"  memory growth: {Measure.Bytes(GC.GetTotalMemory(true) - baseline)}");

        GC.KeepAlive(ticker);
        GC.KeepAlive(ticker2);
    }

    // NoInlining keeps the screens' local variables out of Run, so only the event can keep them alive
    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference[] OpenAndCloseLeakyScreens(PriceTicker ticker)
    {
        var refs = new WeakReference[Screens];
        for (int i = 0; i < Screens; i++)
            refs[i] = new WeakReference(new LeakyQuoteScreen(ticker));   // "user closes the screen" = we drop it
        return refs;
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    private static WeakReference[] OpenAndCloseDisposableScreens(PriceTicker ticker)
    {
        var refs = new WeakReference[Screens];
        for (int i = 0; i < Screens; i++)
        {
            using var screen = new QuoteScreen(ticker);
            refs[i] = new WeakReference(screen);
        }
        return refs;
    }

    private static void ForceFullGc()
    {
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();
    }
}
""", "Internals.Lab.Core/Experiments/EventLeakExperiment.cs")}

<h3>Step 8 — Experiment 6: a real sync-over-async deadlock</h3>
<p>Console apps have no SynchronizationContext, so <code>.Result</code> can't deadlock there. To see the UI-thread deadlock for real, we install a tiny single-threaded context that queues continuations and never runs them while its thread is blocked — exactly what a frozen WinForms thread does.</p>
{C(r"""
using System.Diagnostics;

namespace Internals.Lab.Core.Experiments;

/// <summary>
/// A context like WinForms/WPF/legacy ASP.NET: continuations are queued to ONE thread.
/// We never pump the queue while blocked — exactly what a UI thread stuck in .Result does.
/// </summary>
public sealed class SingleThreadContext : SynchronizationContext
{
    private readonly Queue<(SendOrPostCallback Callback, object? State)> _queue = new();
    public int Pending { get { lock (_queue) return _queue.Count; } }

    public override void Post(SendOrPostCallback d, object? state)
    {
        lock (_queue) _queue.Enqueue((d, state));     // "please run this on my thread later"
    }
}

public sealed class DeadlockExperiment : IExperiment
{
    public string Id => "deadlock";
    public string Title => "6. Sync-over-async deadlock (and why ConfigureAwait(false) avoids it)";
    public string Question => "Blocking with .Wait() on a single-threaded context: does the task ever finish?";

    public void Run(TextWriter output)
    {
        output.WriteLine(Attempt(useConfigureAwaitFalse: false));
        output.WriteLine(Attempt(useConfigureAwaitFalse: true));
        output.WriteLine("Console apps and ASP.NET Core have no such context, so the same code would not deadlock there —");
        output.WriteLine("but it would still block a thread-pool thread. The real fix is async all the way down.");
    }

    private static string Attempt(bool useConfigureAwaitFalse)
    {
        string result = "";
        var uiThread = new Thread(() =>
        {
            var context = new SingleThreadContext();
            SynchronizationContext.SetSynchronizationContext(context);

            var sw = Stopwatch.StartNew();
            Task<decimal> task = GetGstRateAsync(useConfigureAwaitFalse);
            bool finished = task.Wait(TimeSpan.FromSeconds(2));       // ❌ blocking, like .Result
            sw.Stop();

            string label = useConfigureAwaitFalse ? "ConfigureAwait(false)" : "default await";
            result = finished
                ? $"{label,-22}: finished in {sw.ElapsedMilliseconds} ms, rate = {task.Result:P0}"
                : $"{label,-22}: DEADLOCK — gave up after {sw.ElapsedMilliseconds} ms; {context.Pending} continuation(s) stuck in the queue";
        });
        uiThread.Start();
        uiThread.Join();
        return result;
    }

    private static async Task<decimal> GetGstRateAsync(bool configureAwaitFalse)
    {
        await Task.Delay(100).ConfigureAwait(!configureAwaitFalse);   // true = capture the context (default)
        return 0.18m;                                                  // needs the context to run this line
    }
}
""", "Internals.Lab.Core/Experiments/DeadlockExperiment.cs")}
{tip("We use <code>Wait(TimeSpan)</code> with a timeout so the lab reports the deadlock instead of hanging forever. A real <code>.Result</code> has no timeout.")}

<h3>Step 9 — The notebook and Program.cs</h3>
{C(r"""
using System.Runtime;
using System.Runtime.InteropServices;
using Internals.Lab.Core;

namespace Internals.Lab;

/// <summary>Runs an experiment, shows the output and appends it to lab-notebook.md.</summary>
public sealed class LabNotebook(string path)
{
    public void Header()
    {
        if (File.Exists(path)) return;
        File.WriteAllText(path,
            $"# Internals lab notebook{Environment.NewLine}{Environment.NewLine}" +
            $"- Runtime: {RuntimeInformation.FrameworkDescription} on {RuntimeInformation.OSDescription}{Environment.NewLine}" +
            $"- Server GC: {GCSettings.IsServerGC}, latency mode: {GCSettings.LatencyMode}{Environment.NewLine}" +
            $"- Processors: {Environment.ProcessorCount}{Environment.NewLine}");
    }

    public void Record(IExperiment experiment)
    {
        Console.WriteLine();
        Console.WriteLine($"=== {experiment.Title} ===");
        Console.WriteLine($"Predict first: {experiment.Question}");
        Console.Write("Your prediction (Enter to skip): ");
        string prediction = Console.IsInputRedirected ? "" : Console.ReadLine() ?? "";
        if (Console.IsInputRedirected) Console.WriteLine();

        var buffer = new StringWriter();
        experiment.Run(buffer);
        Console.WriteLine(buffer);

        File.AppendAllText(path,
            $"{Environment.NewLine}## {experiment.Title} — {DateTime.Now:dd MMM yyyy HH:mm}{Environment.NewLine}" +
            $"**Question:** {experiment.Question}{Environment.NewLine}{Environment.NewLine}" +
            $"**My prediction:** {(prediction.Length == 0 ? "_(none)_" : prediction)}{Environment.NewLine}{Environment.NewLine}" +
            $"```text{Environment.NewLine}{buffer}```{Environment.NewLine}" +
            $"**What I learned:** {Environment.NewLine}");
    }
}
""", "Internals.Lab/LabNotebook.cs")}
{C(r"""
using System.Runtime;
using Internals.Lab;
using Internals.Lab.Core;
using Internals.Lab.Core.Experiments;

IExperiment[] experiments =
[
    new AllocationExperiment(),
    new GenerationExperiment(),
    new LohExperiment(),
    new SpanParsingExperiment(),
    new EventLeakExperiment(),
    new DeadlockExperiment(),
];

var notebook = new LabNotebook("lab-notebook.md");
notebook.Header();

#if DEBUG
Console.WriteLine("⚠ Debug build: timings are meaningless. Use: dotnet run -c Release");
#endif
Console.WriteLine($"GC mode: {(GCSettings.IsServerGC ? "Server" : "Workstation")}, {GCSettings.LatencyMode}");

// Non-interactive: dotnet run -c Release -- all   |   dotnet run -c Release -- span leak
if (args.Length > 0)
{
    var chosen = args.Contains("all", StringComparer.OrdinalIgnoreCase)
        ? experiments
        : experiments.Where(e => args.Contains(e.Id, StringComparer.OrdinalIgnoreCase)).ToArray();
    foreach (var e in chosen) notebook.Record(e);
    return;
}

while (true)
{
    Console.WriteLine();
    for (int i = 0; i < experiments.Length; i++)
        Console.WriteLine($"  {i + 1}) {experiments[i].Title}");
    Console.WriteLine("  a) Run all   q) Quit");
    Console.Write("Choose: ");
    string? input = Console.ReadLine()?.Trim().ToLowerInvariant();

    if (input is null or "q") break;
    if (input == "a") { foreach (var e in experiments) notebook.Record(e); continue; }
    if (int.TryParse(input, out int n) && n >= 1 && n <= experiments.Length)
        notebook.Record(experiments[n - 1]);
    else
        Console.WriteLine("  ✗ Pick a number from the list.");
}
Console.WriteLine("Results saved to lab-notebook.md");
""", "Internals.Lab/Program.cs")}

<h3>Run it</h3>
{C(r"""
cd Internals.Lab
dotnet run -c Release                    # interactive: type your prediction, then see the result
dotnet run -c Release -- all < /dev/null # everything, no prompts (on Windows: echo. | dotnet run -c Release -- all)
""", lang="bash")}
<p>Sample output from a 2-core Linux VM, .NET 8 (your allocation numbers should match closely; times, GC counts and the small "memory growth" figure for the fixed screens will differ):</p>
{C(r"""
GC mode: Workstation, Interactive

=== 1. What allocates? ===
Case                                      Allocated
int[] of 1,000                               3.9 KB
List<int> + 1,000 Add (no presize)           8.2 KB
List<int>(1,000) presized                    4.0 KB
ArrayList + 1,000 Add (boxing)              31.3 KB
string += 1,000 times                    1,001.9 KB
StringBuilder 1,000 Append                   4.5 KB
1,000 record class Point                    23.4 KB
1,000 record struct Point                       0 B

=== 2. Watching an object get promoted ===
Just allocated:         gen 0
Survived 1 collection:  gen 1
Survived 2 collections: gen 2
Survived 3 collections: gen 2 (gen 2 is the oldest)

After 10,000,000 short-lived invoices (checksum 108888890):
  allocated:        838.5 MB
  gen0 collections: 3
  gen1 collections: 0
  gen2 collections: 0

=== 3. Finding the Large Object Heap threshold ===
 byte[] length  Generation  Heap
         1,000           0  SOH
        80,000           0  SOH
        84,975           0  SOH
        84,976           2  LOH
        85,000           2  LOH
     1,000,000           2  LOH
(On 64-bit an array has a 24-byte header, so 84,976 + 24 = 85,000 bytes.)

new byte[200_000] x 2,000:       gen2 GCs = 16
ArrayPool.Rent(200_000) x 2,000: gen2 GCs = 0

=== 4. Split/Substring vs ReadOnlySpan<char> parsing ===
Approach                    Total (INR)    Allocated       Time
Split + Substring         83,365,523.36      20.6 MB     12.6ms
ReadOnlySpan<char>        83,365,523.36          0 B      3.7ms
Totals match ✓

=== 5. A memory leak through an event — and the fix ===
Leaky screens (no unsubscribe):
  still alive:   50 of 50
  subscribers:   50
  memory growth: 47.7 MB
Disposable screens (unsubscribe in Dispose):
  still alive:   0 of 50
  subscribers:   0
  memory growth: -6.0 KB

=== 6. Sync-over-async deadlock (and why ConfigureAwait(false) avoids it) ===
default await         : DEADLOCK — gave up after 2004 ms; 1 continuation(s) stuck in the queue
ConfigureAwait(false) : finished in 102 ms, rate = 18 %
""", lang="text")}
<p class="muted">Why only 3 gen 0 collections for 838 MB of garbage? The gen 0 budget is sized from the CPU cache and adapts to the allocation rate; on this VM it was large. On a laptop you may see dozens. The point stands: none of it reached gen 1 or 2.</p>

<h3>Record your results</h3>
<p>Copy this table into <code>lab-notebook.md</code> (or your blog draft) and fill it in from your own run.</p>
{table(["Experiment","My prediction","Measured","Surprised? Why?"],[
["1. ArrayList vs List&lt;int&gt; bytes","","",""],
["1. string += vs StringBuilder","","",""],
["1. record class vs record struct","","",""],
["2. Generation after 0/1/2/3 GCs","","",""],
["3. First LOH length","","",""],
["3. Gen 2 GCs: new vs ArrayPool","","",""],
["4. Bytes and time: Split vs Span","","",""],
["5. Leaky screens still alive","","",""],
["6. Did the default await deadlock?","","",""]])}

<h3>Step 10 (optional) — Confirm with BenchmarkDotNet</h3>
{C(r"""
dotnet new console -n Internals.Lab.Bench
dotnet sln add Internals.Lab.Bench
dotnet add Internals.Lab.Bench reference Internals.Lab.Core
dotnet add Internals.Lab.Bench package BenchmarkDotNet
""", lang="bash")}
{C(r"""
using BenchmarkDotNet.Attributes;
using BenchmarkDotNet.Running;
using Internals.Lab.Core.Experiments;

BenchmarkRunner.Run<ParserBenchmarks>();

[MemoryDiagnoser]                         // adds Allocated and Gen0 columns
public class ParserBenchmarks
{
    private string[] _lines = [];

    [GlobalSetup]
    public void Setup() =>
        _lines = Enumerable.Range(0, 10_000)
                           .Select(i => $"ORD-{i}|{(i % 2 == 0 ? "560001" : "400001")}|{i % 5000}.50|KA")
                           .ToArray();

    [Benchmark(Baseline = true)]
    public decimal SplitSubstring() => SpanParsingExperiment.TotalForPinPrefixClassic(_lines, "56");

    [Benchmark]
    public decimal Span() => SpanParsingExperiment.TotalForPinPrefixSpan(_lines, "56");
}
""", "Internals.Lab.Bench/Program.cs")}
{C(r"""
dotnet run -c Release --project Internals.Lab.Bench
# Prints a table with Mean, Error, StdDev, Ratio, Gen0 and Allocated per method.
# Expect Span's Allocated column to read "-" (zero) and its Ratio to be well below 1.00.
""", lang="bash")}

<h3>The blog post: \"What I learned about .NET's GC and async\"</h3>
<p>Write 800–1,200 words in your own words, using your own numbers. Don't copy these notes; if you can't explain a section without looking, that's the section to re-study. Fill in each prompt:</p>
{C(r"""
# What I learned about .NET's garbage collector and async (with experiments)

> One-sentence hook: the most surprising number from your lab, e.g. "Parsing 100,000 order lines
> allocated 20.6 MB with Split() and 0 bytes with spans."

## 1. Why I ran these experiments
- What did you believe about memory in .NET before this week?
- Which "fact" turned out to be a myth (stack vs heap)?

## 2. Where my data actually lives
- Explain stack vs heap precisely, in 3–4 sentences, with one example from your own code.
- Explain boxing using experiment 1's ArrayList number.

## 3. How the GC decides what to throw away
- Roots, reachability, mark and compact — explain with a diagram or an analogy of your own.
- Paste your generation-promotion output (experiment 2) and explain each line.
- Why does "most objects die young" make generations a good design?

## 4. The 85,000-byte cliff
- What did you predict for experiment 3 and what happened?
- Why is churning large arrays expensive, and how did ArrayPool change the gen 2 count?

## 5. Allocating less with Span<T>
- Show the two parsers side by side (short snippets) and your measured table.
- When would you NOT bother with spans?

## 6. How I leaked 50 MB with one line of code
- Explain the event leak as if to a teammate in a code review.
- The fix, and two other leak sources you'd look for (static caches, timers, closures).

## 7. Async: the deadlock I built on purpose
- Explain SynchronizationContext in plain words.
- Walk through the four steps of the .Result deadlock using experiment 6's output.
- Why ConfigureAwait(false) helped, and why "async all the way" is the real fix.
- Why ASP.NET Core doesn't deadlock but still suffers from sync-over-async (thread-pool starvation).

## 8. How I'd investigate this in production
- Which dotnet-counters metrics you'd watch, and what dotnet-dump's gcroot would show for the leak.

## 9. Five rules I'm taking away
1. ...
2. ...
3. ...
4. ...
5. ...

## Environment
.NET version, OS, CPU, Workstation/Server GC (copy from the top of lab-notebook.md).
Code: link to your GitHub repo.
""", "blog/gc-and-async.md", lang="markdown")}

<h3>Stretch goals</h3>
<ul>
<li>Add experiment 7: a class with a finalizer vs without; allocate 1 million of each and compare time and gen counts.</li>
<li>Add experiment 8: a closure capturing a 5 MB array stored in a static list; show it stays alive, then fix it.</li>
<li>Run the lab with <code>DOTNET_gcServer=1</code> and compare GC counts; record the difference in the notebook.</li>
<li>Run <code>dotnet-counters monitor -n Internals.Lab</code> in a second terminal while the leak experiment runs in a loop.</li>
</ul>
''',
iqs=[("Basic","Why must you run benchmarks in Release and warm up first?","Debug builds disable JIT optimisations, and the first call includes JIT compilation and static initialisation. Release plus warm-up (or BenchmarkDotNet, which does it for you with statistics) measures the steady-state code your users actually run."),
("Basic","How did you prove the event caused the leak?","By holding only WeakReferences to the screens, forcing a full GC and checking IsAlive: all 50 leaky screens survived and the ticker reported 50 subscribers. The disposable version that unsubscribes had 0 survivors. In production, dotnet-dump's gcroot would show the path ticker → delegate → screen."),
("Intermediate","Why does the span parser allocate nothing while Split allocates ~20 MB?","Split creates a string[] plus one new string per field for every line. The span version only moves a pointer and length over the existing string, and decimal.Parse has a ReadOnlySpan&lt;char&gt; overload, so no intermediate strings are ever created."),
("Intermediate","Your deadlock demo needed a custom SynchronizationContext. What does that tell you about where .Result deadlocks occur?","Only where a single-threaded context captures continuations: UI frameworks and legacy ASP.NET. Console apps and ASP.NET Core have no context, so continuations run on the thread pool. There, blocking doesn't deadlock but wastes threads and can starve the pool under load.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Revise Weeks 5–8: LINQ, I/O, async and internals",
"Consolidate the second month: test yourself on LINQ, files/JSON/config/logging, async and concurrency, and .NET internals; finish and publish the lab.",
[("Active recall","Answering from memory before checking the notes."),
("Interleaving","Mixing questions from different topics, which is harder than block revision but sticks better."),
("Mock interview","Answering out loud under a time limit, ideally recorded, to practise structure as well as content.")],
["Close the notes before every quiz and checklist below.",
"Mark each checklist item green / amber / red; only re-study ambers and reds.",
"Answer mock interview questions aloud in two minutes: definition, example, pitfall.",
"Finish the lab README and push before you start revising, so it's done.",
"Publish (or at least commit) the blog post from Saturday."],
f'''
<h3>1. How to spend today (≈4 hours)</h3>
{table(["Time","Activity"],[
["30 min","Finish the lab: \"try to break it\" checks, README, push"],
["40 min","Blank-page recall: one page per week (5, 6, 7, 8), from memory"],
["30 min","Mark the checklists below green/amber/red"],
["50 min","Re-study reds; type one example per red topic"],
["30 min","Mixed quiz (8 questions)"],
["40 min","Mock interview aloud; record yourself and listen back once"]])}

<h3>2. Finish the lab</h3>
<h4>Try to break it</h4>
{table(["Try this","Expected / what to learn"],[
["Run in Debug (<code>dotnet run</code>)","Warning banner; allocation numbers similar, timings worse — and the leak test may show a few extra survivors because Debug extends local lifetimes"],
["Run with <code>DOTNET_gcServer=1</code>","Header shows Server GC; gen 0 counts drop (bigger budgets)"],
["<code>dotnet run -c Release -- nonsense</code>","Nothing runs; consider printing the valid ids instead"],
["Remove <code>[MethodImpl(NoInlining)]</code> from the leak helpers","Usually no change in Release, but the test becomes fragile: the JIT may extend lifetimes"],
["Change <code>ConfigureAwait(!configureAwaitFalse)</code> to always <code>true</code>","Both attempts deadlock"],
["Change a line in the span parser's input to have only three fields","<code>ArgumentOutOfRangeException</code> from slicing: add the -1 checks from the note"],
["Raise LOH test sizes to 10 MB and loop 20,000 times","Gen 2 count rises sharply; memory spikes; ArrayPool line stays at 0 (until requests exceed the pool's largest bucket)"]])}
<h4>README</h4>
{C(r"""
# Internals Lab

Week 8 project of my .NET full-stack roadmap: six small experiments that make
the CLR's memory management and async behaviour visible.

## Experiments
1. What allocates (boxing, string concatenation, records vs record structs)
2. Generation promotion with GC.GetGeneration
3. The 85,000-byte Large Object Heap threshold, and ArrayPool
4. Split/Substring vs ReadOnlySpan<char> parsing (allocations + time)
5. A memory leak through an event, and the Dispose fix
6. A real sync-over-async deadlock with a single-threaded SynchronizationContext

## Run
```bash
dotnet run -c Release --project Internals.Lab            # interactive
dotnet run -c Release --project Internals.Lab -- all     # all experiments
dotnet run -c Release --project Internals.Lab.Bench      # BenchmarkDotNet (optional)
```
Results and predictions are appended to `lab-notebook.md`.

## What I learned
See [my write-up](blog/gc-and-async.md).
""", "README.md", lang="markdown")}
{C(r"""
git init
dotnet new gitignore
git add .
git commit -m "Internals lab: allocation, GC generations, LOH, span parsing, event leak, deadlock demo"
git branch -M main
git remote add origin https://github.com/<your-username>/internals-lab.git
git push -u origin main
""", lang="bash")}

<h3>3. Month-2 checklist</h3>
<h4>Week 5 — Delegates, lambdas and LINQ</h4>
<ul><li>Func/Action/Predicate; lambdas; closures and the loop-variable capture</li><li>Where, Select, SelectMany, OrderBy/ThenBy, GroupBy, Join, aggregates (Sum, Count, Min/MaxBy, Aggregate)</li><li>Deferred vs immediate execution; which operators materialise (ToList, Count, First…)</li><li>Multiple enumeration; First vs Single vs FirstOrDefault</li><li>IEnumerable vs IQueryable (delegates in memory vs expression trees translated to SQL)</li></ul>
<h4>Week 6 — Files, JSON, configuration and logging</h4>
<ul><li>File / Directory / Path; streams, StreamReader/Writer, <code>using</code> and <code>await using</code></li><li>Reading big files line by line (File.ReadLines) vs all at once</li><li>System.Text.Json: serialise/deserialise, options, naming policy, attributes, source generation</li><li>IConfiguration: appsettings.json, environment overrides, environment variables, the options pattern</li><li>ILogger: levels, structured logging with message templates, providers</li></ul>
<h4>Week 7 — Async and concurrency</h4>
<ul><li>Task vs Thread; async/await state machine; Task vs ValueTask</li><li>Task.WhenAll / WhenAny; cancellation with CancellationToken; timeouts</li><li>Exceptions in async code; AggregateException; await unwrapping the first exception</li><li>Race conditions; lock, Interlocked, SemaphoreSlim; concurrent collections</li><li>Producer/consumer with Channel&lt;T&gt;; Parallel.ForEachAsync</li></ul>
<h4>Week 8 — .NET internals</h4>
<ul><li>CLR, IL, JIT tiers, Dynamic PGO, ReadyToRun vs Native AOT</li><li>Assemblies and metadata; NuGet versions, lock files, CPM, vulnerability audit</li><li>Stack vs heap (precisely); GC roots, generations, LOH, GC modes; finalizers vs Dispose</li><li>Span/ReadOnlySpan/Memory, stackalloc, ArrayPool; ref struct rules</li><li>Reflection, custom attributes, cost, source generators</li><li>async void, sync-over-async deadlocks, fire-and-forget, leak sources, dotnet-counters/dump</li></ul>

<h3>4. Cheat sheet</h3>
{table(["Topic","Remember","Classic trap"],[
["LINQ execution","Where/Select/OrderBy are deferred; ToList/Count/First/Sum run immediately","Enumerating a query twice runs it twice"],
["First / Single","First: at least one; Single: exactly one; *OrDefault returns default instead of throwing","Single on a list with duplicates throws"],
["IEnumerable vs IQueryable","Delegates run in memory vs expression tree translated by a provider","Calling AsEnumerable/ToList too early pulls the whole table"],
["Files","<code>using</code> every stream; File.ReadLines streams, ReadAllLines loads everything","Undisposed writer: data not flushed, file locked"],
["JSON","Default property names are as declared (PascalCase); Web defaults use camelCase","Case mismatch on deserialise silently leaves properties at default"],
["Configuration","Later sources override earlier: appsettings → appsettings.{Env} → env vars → command line","Nested keys in env vars use <code>__</code> (double underscore)"],
["Logging","Message templates: <code>LogInformation(\"Order {Id}\", id)</code>, not interpolation","Interpolated strings lose structure and allocate even when the level is off"],
["async/await","Async all the way; return Task; pass CancellationToken","async void; .Result; forgotten await"],
["WhenAll","Runs tasks concurrently; await throws the first exception (all are in task.Exception)","Awaiting in a loop serialises the work"],
["Thread safety","lock for compound operations, Interlocked for counters, SemaphoreSlim across await","<code>lock</code> can't contain await"],
["Memory","Value types live where their container lives; objects always on the heap","\"Structs are always on the stack\""],
["GC","Gen 0 cheap and frequent, gen 2 expensive; LOH ≥ 85,000 bytes","GC.Collect in app code; per-request large buffers"],
["Span","No-copy slicing; stack-only; Memory&lt;T&gt; across await","Calling ToString on every slice"],
["Reflection","Cache MemberInfo; prefer delegates or source generators on hot paths","Lookups in loops; breaks under trimming/AOT"],
["Leaks","Events, statics, timers, closures, undisposed resources","Fixing with restarts instead of gcroot"]])}

<h3>5. Mixed quiz — predict the output</h3>
<details><summary>Q1. (Week 5) What prints?</summary>
{C(r"""
var cities = new List<string> { "Pune", "Patna" };
var pCities = cities.Where(c => c.StartsWith('P'));
cities.Add("Panaji");
cities.Add("Delhi");
Console.WriteLine(pCities.Count());
""")}<b>3.</b> Where is deferred; the filter runs when Count() enumerates, after Panaji was added.</details>
<details><summary>Q2. (Week 6) What prints?</summary>
{C(r"""
using System.Text.Json;

string json = JsonSerializer.Serialize(new Person("Asha", 30));
Person? back = JsonSerializer.Deserialize<Person>("{\"name\":\"Ravi\",\"age\":41}");
Console.WriteLine(json);
Console.WriteLine(back);

public class Person(string name, int age)
{
    public string Name { get; set; } = name;
    public int Age { get; set; } = age;
    public override string ToString() => $"{Name} ({Age})";
}
""")}<b>{{"Name":"Asha","Age":30}} then " (0)".</b> Serialisation uses the declared (PascalCase) names. Deserialisation is case-sensitive by default, so "name"/"age" match neither the properties nor the constructor parameters; the constructor gets null and 0. Use <code>JsonSerializerOptions.Web</code> (.NET 9) or <code>new JsonSerializerOptions(JsonSerializerDefaults.Web)</code> / <code>PropertyNameCaseInsensitive = true</code> to get <code>Ravi (41)</code>.</details>
<details><summary>Q3. (Week 7) What prints?</summary>
{C(r"""
static async Task Work()
{
    Console.Write("B");
    await Task.Delay(10);
    Console.Write("D");
}

Console.Write("A");
Task t = Work();
Console.Write("C");
await t;
Console.Write("E");
""")}<b>ABCDE.</b> An async method runs synchronously until its first incomplete await, so B prints before control returns and C prints.</details>
<details><summary>Q4. (Week 7) What prints?</summary>
{C(r"""
static async Task Fail(string name, int delayMs)
{
    await Task.Delay(delayMs);
    throw new InvalidOperationException(name);
}

try
{
    await Task.WhenAll(Fail("GST", 100), Fail("TDS", 10));
}
catch (Exception ex)
{
    Console.WriteLine(ex.Message);
}
""")}<b>TDS</b> (verified on .NET 8). await on WhenAll rethrows only the first exception in the combined task's <code>Exception.InnerExceptions</code>; on .NET 8 those are collected as the tasks complete, so TDS (failing after 10 ms) comes first. Don't rely on which one you get: inspect the WhenAll task's <code>Exception.InnerExceptions</code> to see all of them.</details>
<details><summary>Q5. (Week 8) What prints?</summary>
{C(r"""
var invoices = new byte[50_000];
var scans    = new byte[100_000];
Console.WriteLine($"{GC.GetGeneration(invoices)} {GC.GetGeneration(scans)}");
""")}<b>0 2.</b> The 100,000-byte array is on the Large Object Heap, which is reported as generation 2 from the start.</details>
<details><summary>Q6. (Week 8) What prints?</summary>
{C(r"""
string city = "Bengaluru";
ReadOnlySpan<char> s = city.AsSpan(0, 4);
Console.WriteLine($"{s.ToString()} {s.Length} {city.AsSpan()[^3..].ToString()}");
""")}<b>Beng 4 uru.</b> AsSpan(start, length) and the <code>^3..</code> range both slice without copying; ToString creates the strings only for printing.</details>
<details><summary>Q7. (Week 8) Does this compile?</summary>
{C(r"""
public class CsvImporter
{
    private Span<char> _buffer = new char[256];
    public int Size => _buffer.Length;
}
""")}<b>No.</b> CS8345: a field of a class can't be of a ref struct type like Span&lt;char&gt;. Use <code>Memory&lt;char&gt;</code> or <code>char[]</code>.</details>
<details><summary>Q8. (Week 8) What prints?</summary>
{C(r"""
using System.Reflection;

Console.WriteLine(typeof(Order).GetProperties().Length);
Console.WriteLine(typeof(Order).GetProperties(BindingFlags.NonPublic | BindingFlags.Instance).Length);

public record Order(int Id, string Customer);
""")}<b>2 then 1.</b> The public properties are Id and Customer. Records also generate a <code>protected virtual Type EqualityContract</code> property, which only appears when you ask for non-public members.</details>

<h3>6. Mock interview (answer aloud, 2 minutes each)</h3>
<ol>
<li>Explain deferred execution in LINQ and a bug it caused (or could cause) in your Week 5 project.</li>
<li>IEnumerable vs IQueryable: what happens to a <code>Where</code> on each?</li>
<li>How does configuration layering work in .NET, and how would you keep a database password out of appsettings.json?</li>
<li>Why use message templates instead of string interpolation in logging?</li>
<li>Explain what <code>await</code> does to a method, and why async isn't the same as multithreaded.</li>
<li>You need to call five slow APIs and combine the results with a 3-second overall timeout. Walk me through the code.</li>
<li>Where do value types live? Be precise.</li>
<li>Walk me through a gen 0 garbage collection. What is the LOH and why does it matter?</li>
<li>When would you use Span&lt;T&gt;, and when Memory&lt;T&gt;?</li>
<li>How do serializers and validation frameworks use reflection, and how do source generators change that?</li>
<li>A service's memory grows until the container restarts every night. How do you investigate?</li>
<li>Why can <code>.Result</code> deadlock a WPF app but not an ASP.NET Core app? Is it then fine in ASP.NET Core?</li>
</ol>

<div class="note tip"><b>Next week:</b> Week 9 — SOLID principles and design patterns. You'll take code that works and make it easy to change: single responsibility, open/closed with strategies, Liskov traps, interface segregation and dependency inversion, then Factory, Strategy, Decorator, Observer, Adapter and friends, applied by refactoring an earlier project.</div>
''',
iqs=[("Basic","What is the difference between deferred and immediate execution in LINQ?","Deferred operators (Where, Select, OrderBy, GroupBy…) build a query that runs only when enumerated, every time it's enumerated, against the source's current contents. Immediate operators (ToList, ToArray, Count, Sum, First, Any…) enumerate right away and return a result. Materialise once with ToList when you need the results more than once."),
("Intermediate","How does await relate to threads?","await doesn't create a thread. It registers a continuation and returns an incomplete task to the caller, freeing the current thread. When the awaited operation (often I/O with no thread at all) completes, the continuation runs on the captured context or a thread-pool thread. Async improves scalability; parallelism comes from running multiple tasks concurrently."),
("Intermediate","How would you reduce allocations in a hot JSON or CSV processing path?","Measure first (BenchmarkDotNet MemoryDiagnoser, dotnet-counters alloc rate). Then stream instead of loading whole files, parse with spans and span-based Parse overloads, reuse buffers with ArrayPool, use System.Text.Json source generation or Utf8JsonReader, avoid LINQ and closures in the innermost loop, and only create strings for values you keep."),
("Intermediate","A colleague says \"we have a GC, so we can't have memory leaks.\" How do you respond?","The GC frees unreachable objects, but leaks in .NET are reachable objects you no longer need: event subscriptions to long-lived publishers, static or unbounded caches, timers whose callbacks capture objects, closures held by long-lived lists, and undisposed resources holding native memory and handles. You find them with dumps and gcroot, and fix them by removing the reference.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","CLR, IL, JIT, assemblies and NuGet","CLR · IL · NuGet","From C# to native code, reading IL, tiered JIT and PGO, R2R vs Native AOT, package versions and audits.","2 hrs"),
 (2,"TUE","Stack vs heap and the garbage collector","Stack, heap &amp; GC","Where data really lives, GC roots, generations, LOH, GC modes, finalizers vs Dispose.","2 hrs"),
 (3,"WED","Span, Memory, stackalloc and ArrayPool","Span &amp; ArrayPool","Zero-copy slicing, allocation-free parsing, ref struct rules, pooled buffers.","2 hrs"),
 (4,"THU","Reflection and attributes","Reflection","Types, properties, Activator, invoking methods, a mini validation framework, cost and source generators.","2 hrs"),
 (5,"FRI","Async and GC pitfalls, leaks and diagnostics","Pitfalls &amp; diagnostics","async void, sync-over-async deadlocks, fire-and-forget, leak sources, dotnet-counters and dotnet-dump.","2 hrs"),
 (6,"SAT","Internals lab and blog post","Project: internals lab","Six measured experiments (GC, LOH, Span, leak, deadlock) and a write-up in your own words.","4 hrs"),
 (7,"SUN","Revise Weeks 5–8","Month-2 revision","Finish the lab, checklists, cheat sheet, mixed quiz, mock interview.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week08.html", 8,
      "Week 8 — .NET internals", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 8 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Internals lab"],
      "This week you look under the hood: how C# becomes IL and then native code, where your data really lives, how the garbage collector decides what to free, how Span and ArrayPool avoid allocations, how reflection and attributes power frameworks, and which async and memory mistakes take down real systems. Saturday you measure all of it in a lab and explain it in your own words; Sunday revises the whole second month.",
      cards, days)
print("built")
