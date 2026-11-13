import sys; sys.path.insert(0, "/home/claude/build")
from lib import *

# ================= DAY 1 =================
d1 = day(1, "MON", "Git: branching, merge vs rebase, conflicts, pull requests and releases",
"Work the way professional teams do: short-lived branches, clean history, confident conflict resolution, reviewed pull requests, conventional commit messages and tagged releases.",
[("Repository","A project folder plus its full history, stored in the hidden <code>.git</code> directory."),
("Commit","An immutable snapshot of the tracked files, identified by a SHA hash, with a message, author and parent commit(s)."),
("Branch","A movable label pointing at one commit. Creating a branch is cheap: Git writes a 41-byte file."),
("HEAD","A pointer to what you have checked out, usually a branch name. A <i>detached HEAD</i> points straight at a commit."),
("Remote / origin","Another copy of the repository, usually on GitHub. <code>origin</code> is the default name for the one you cloned from."),
("Fast-forward merge","A merge where the target branch has no new commits, so Git just moves its label forward. No merge commit is created."),
("Merge commit","A commit with two parents, created by a three-way merge when both branches have moved on."),
("Rebase","Re-applying your commits one by one on top of another base commit, creating new commits with new hashes."),
("Interactive rebase","<code>git rebase -i</code>: edit a list of your commits to reorder, reword, squash, fix up or drop them before sharing."),
("Merge conflict","Both sides changed the same lines (or one deleted what the other edited); Git stops and asks you to choose."),
("Pull request (PR)","A GitHub request to merge one branch into another, with a diff, discussion, review approvals and CI checks."),
("Conventional Commits","A message format, <code>type(scope): summary</code>, e.g. <code>feat(bank): add daily limit</code>, that tools can parse for changelogs and versions."),
("Tag","A named pointer to a commit, used for releases. Annotated tags (<code>-a</code>) store a message, author and date; lightweight tags don't."),
(".gitattributes","A file telling Git how to treat paths: line-ending normalisation, diff drivers, binary files."),
("Reflog","Your local log of where HEAD and branches have pointed. It lets you recover \"lost\" commits after a bad reset or rebase.")],
["Branch per change, keep it short-lived (a day or two), merge through a PR.",
"Merge preserves history exactly; rebase rewrites it into a straight line.",
"Golden rule: never rebase commits that others have already pulled.",
"After rebasing your own pushed branch use <code>git push --force-with-lease</code>, never plain <code>--force</code>.",
"A conflict is normal, not an error: edit the file, <code>git add</code> it, continue.",
"Commit messages describe <i>why</i>; the diff already shows <i>what</i>."],
f'''
<h3>1. Branches and the everyday GitHub flow</h3>
<p>A branch is just a label on a commit. When you commit, the label you're on moves forward. The common team workflow (often called <b>GitHub flow</b>) is: <code>main</code> is always deployable; every change happens on a branch; the branch is merged through a pull request after review and green CI.</p>
{C(r"""
# One-time setup
git config --global user.name  "Samrath"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase true          # pull = fetch + rebase instead of a merge commit
git config --global rebase.autoStash true     # stash/unstash uncommitted work around a rebase

# Start a change from an up-to-date main
git switch main
git pull
git switch -c feat/bank-daily-limit           # create and switch (older syntax: git checkout -b)

# ...edit files...
git status
git add Bank.Core/Account.cs
git commit -m "feat(bank): enforce daily withdrawal limit"

git push -u origin feat/bank-daily-limit      # -u links local and remote branch once
git branch -vv                                # shows each branch and what it tracks

# See the shape of history
git log --oneline --graph --decorate --all
# * 9f1c2ab (HEAD -> feat/bank-daily-limit, origin/feat/bank-daily-limit) feat(bank): enforce daily withdrawal limit
# * 41d07e3 (origin/main, main) docs: add README for bank simulator
# * 0b6a1f9 feat(bank): savings and current accounts
""", lang="bash")}
{table(["Branch prefix","Use for","Example"],[
["<code>feat/</code>","New behaviour","<code>feat/library-reservations</code>"],
["<code>fix/</code>","Bug fix","<code>fix/negative-gst-rounding</code>"],
["<code>refactor/</code>","Internal change, same behaviour","<code>refactor/expense-repository</code>"],
["<code>docs/</code>, <code>test/</code>, <code>ci/</code>","Docs, tests, pipeline","<code>ci/add-dotnet-workflow</code>"],
["<code>release/</code>, <code>hotfix/</code>","Git-flow style teams only","<code>hotfix/1.2.1</code>"]])}

<h3>2. Merging: fast-forward vs merge commit</h3>
<p><b>Case A — main hasn't moved.</b> Your branch simply continues main's line, so Git can <i>fast-forward</i>: move the main label to your last commit. No new commit appears.</p>
{C(r"""
Before                                   After: git switch main && git merge feat
A ── B ── C            (main)            A ── B ── C ── D ── E   (main, feat)
           \
            D ── E     (feat)
""", lang="text")}
<p><b>Case B — main has new commits.</b> Git does a <i>three-way merge</i> using the common ancestor (C), your tip (E) and main's tip (F), and records a <b>merge commit</b> M with two parents.</p>
{C(r"""
Before                                   After: git switch main && git merge feat
A ── B ── C ── F        (main)           A ── B ── C ── F ────── M   (main)
           \                                        \           /
            D ── E      (feat)                       D ── E ───┘     (feat)
""", lang="text")}
{C(r"""
git switch main
git merge feat/bank-daily-limit             # fast-forwards if it can, otherwise creates a merge commit
git merge --no-ff feat/bank-daily-limit     # ALWAYS create a merge commit (keeps the branch visible in history)
git merge --ff-only feat/bank-daily-limit   # refuse unless a fast-forward is possible
git branch -d feat/bank-daily-limit         # delete the merged local branch (-D forces even if unmerged)
git push origin --delete feat/bank-daily-limit
""", lang="bash")}

<h3>3. Rebase and interactive rebase</h3>
<p><code>git rebase main</code> (run while on your branch) takes your commits D and E, sets them aside, moves your branch to main's tip, and re-applies them as <b>new</b> commits D′ and E′. History becomes a straight line and main can then fast-forward.</p>
{C(r"""
Before                                   After: git switch feat && git rebase main
A ── B ── C ── F        (main)           A ── B ── C ── F             (main)
           \                                             \
            D ── E      (feat)                            D' ── E'    (feat)   <- new hashes
""", lang="text")}
{C(r"""
git switch feat/expense-export
git fetch origin
git rebase origin/main                 # replay my commits on the latest main
# If a conflict appears: fix files, then
git add Expense.Core/CsvExporter.cs
git rebase --continue                  # or: git rebase --skip  /  git rebase --abort (back to where you started)

git push --force-with-lease            # my branch was already pushed, and rebase changed its hashes
""", lang="bash")}
<h4>Interactive rebase — clean up before you open the PR</h4>
<p>You'll run this locally; here is what you'll see. <code>git rebase -i HEAD~4</code> opens your editor with the last four commits, <b>oldest first</b>. Change the command word on each line, save and close.</p>
{C(r"""
pick 3a1f0c2 feat(expense): add CSV export
pick 8be44d1 wip
pick c91d7a0 fix typo in header row
pick 5d2e9b3 test(expense): cover CSV export

# Commands:
# p, pick   = use commit
# r, reword = use commit, but edit the message
# e, edit   = use commit, but stop so you can amend it
# s, squash = meld into previous commit, combine both messages
# f, fixup  = meld into previous commit, discard this message
# d, drop   = remove commit
""", "git-rebase-todo (as opened)", lang="text")}
{C(r"""
pick 3a1f0c2 feat(expense): add CSV export
fixup 8be44d1 wip
fixup c91d7a0 fix typo in header row
pick 5d2e9b3 test(expense): cover CSV export
""", "git-rebase-todo (after your edit) → 2 clean commits", lang="text")}
{C(r"""
# Even easier: mark fixes as you go, let Git arrange them
git commit --fixup 3a1f0c2             # creates "fixup! feat(expense): add CSV export"
git rebase -i --autosquash origin/main # fixup lines are placed and marked automatically

# Undo almost anything: the reflog remembers where your branch was
git reflog
# 5d2e9b3 HEAD@{0}: rebase (finish): returning to refs/heads/feat/expense-export
# 77aa013 HEAD@{5}: commit: test(expense): cover CSV export
git reset --hard HEAD@{5}            # jump back to the pre-rebase state
""", lang="bash")}
{warn("Never rebase a branch other people have pulled (main, a shared release branch). Rebase creates new commits; everyone else still has the old ones, and their next pull duplicates or conflicts with your work. Rebase <i>your own</i> feature branch; merge shared ones.", "Golden rule")}
{table(["","Merge (merge commit)","Rebase then fast-forward","Squash merge"],[
["History shape","Branchy, true record of what happened","Linear","Linear, one commit per PR"],
["Rewrites commits?","No","Yes — new hashes","Creates one new commit; branch commits are discarded"],
["Safe on shared branches?","Yes","No","Yes (done by GitHub on merge)"],
["Conflicts resolved","Once, in the merge commit","Possibly once per replayed commit","Once"],
["git bisect / blame","Works, can be noisy","Clean","Clean but coarse (whole PR in one commit)"],
["Typical use","Merging release/long-lived branches","Updating your feature branch from main","GitHub \"Squash and merge\" for small PRs"]])}

<h3>4. Resolving conflicts</h3>
<p>You and a teammate both changed the daily limit. Git stops and writes both versions into the file between markers:</p>
{C(r"""
public abstract class Account
{
<<<<<<< HEAD
    public const decimal DailyWithdrawalLimit = 100_000m;
=======
    public const decimal DailyWithdrawalLimit = 50_000m;   // RBI-style limit for new accounts
>>>>>>> feat/new-account-limits
""", "Bank.Core/Account.cs (conflicted — does not compile)", lang="text")}
<p>During a <b>merge</b>, <code>HEAD</code> is the branch you're on and the bottom half is the branch being merged in. During a <b>rebase</b> the sides are swapped: <code>HEAD</code> is the base you're replaying onto (main), and the bottom half is your own commit. Read the labels, don't assume.</p>
{C(r"""
git status                              # "both modified: Bank.Core/Account.cs"
git diff                                # shows the conflict hunks

# Option 1: edit the file by hand (or in VS Code / Rider's 3-way merge editor), remove ALL markers
# Option 2: take one side completely
git checkout --ours   Bank.Core/Account.cs
git checkout --theirs Bank.Core/Account.cs

dotnet build && dotnet test             # never commit a resolution you haven't compiled
git add Bank.Core/Account.cs            # 'add' marks the conflict as resolved
git commit                              # during a merge   (or: git rebase --continue during a rebase)

git merge --abort                       # panic button: back to before the merge
git config --global rerere.enabled true # "reuse recorded resolution": Git remembers how you fixed a hunk
""", lang="bash")}
{tip("The best conflict prevention is small, short-lived branches and pulling main into your branch daily. Two-week-old branches are where painful conflicts come from.")}

<h3>5. Pull requests and conventional commits</h3>
<p>A good PR is small (ideally under ~400 changed lines), has one purpose, explains the <i>why</i>, shows how it was tested, and has green CI before anyone reviews it.</p>
{C(r"""
# GitHub CLI (gh) — open a PR from the terminal
gh auth login
gh pr create --base main --title "feat(bank): enforce daily withdrawal limit" \
             --body "Closes #12. Adds DailyLimitExceededException; tests in AccountTests."
gh pr status
gh pr checks                     # CI results
gh pr merge --squash --delete-branch
""", lang="bash")}
{C(r"""
## What
Enforce a ₹1,00,000 daily withdrawal limit on all accounts.

## Why
Requirement from the Week 3 spec; prevents large fraudulent withdrawals.

## How
- `Account.Debit` sums today's debits from the ledger before allowing a new one
- New `DailyLimitExceededException` carries `Limit` and `UsedToday`

## Testing
- [x] `dotnet test` — 3 new tests in `AccountTests`
- [x] Manual: withdrew 60,000 then 50,000 → second rejected

## Screenshots
(n/a — console app)
""", ".github/pull_request_template.md", lang="markdown")}
<h4>Conventional Commits</h4>
{table(["Type","Meaning","Example"],[
["<code>feat</code>","New feature (minor version bump)","<code>feat(library): add reservation queue</code>"],
["<code>fix</code>","Bug fix (patch bump)","<code>fix(expense): round GST to 2 decimals</code>"],
["<code>refactor</code>","Code change, no behaviour change","<code>refactor(parking): extract IPricingStrategy</code>"],
["<code>test</code>","Adding or fixing tests","<code>test(bank): cover transfer rollback</code>"],
["<code>docs</code>","Documentation only","<code>docs: add architecture diagram to README</code>"],
["<code>perf</code>, <code>style</code>, <code>build</code>, <code>ci</code>, <code>chore</code>","Performance, formatting, build system, pipeline, housekeeping","<code>ci: run tests on pull requests</code>"],
["<code>!</code> or <code>BREAKING CHANGE:</code> footer","Breaking change (major bump)","<code>feat(api)!: rename /accounts to /v2/accounts</code>"]])}
{C(r"""
git commit -m "fix(expense): round GST to 2 decimals" \
           -m "Totals were off by a paisa because rounding happened per line instead of per invoice." \
           -m "Closes #31"
# subject: imperative mood, <= 72 chars, no full stop; body: why; footer: issue links / BREAKING CHANGE
""", lang="bash")}

<h3>6. .gitignore, .gitattributes, tags and releases</h3>
{C(r"""
dotnet new gitignore             # the official .NET .gitignore: bin/, obj/, .vs/, *.user, TestResults/ ...
git rm -r --cached .             # if bin/obj were already committed: untrack everything (files stay on disk)...
git add .                        # ...and re-add: the new .gitignore now excludes bin/ and obj/ in every project
git commit -m "chore: stop tracking build output"
git check-ignore -v Bank.App/bin/Debug/net8.0/Bank.App.dll   # which rule ignores this file?
""", lang="bash")}
{C(r"""
# Normalise line endings in the repo (LF), convert on checkout as the platform needs
* text=auto

# Source files: always text, use C#-aware diff hunk headers
*.cs     text diff=csharp
*.csproj text
*.sln    text eol=crlf
*.sh     text eol=lf

# Never try to merge or diff these as text
*.png    binary
*.jpg    binary
*.gif    binary
*.pdf    binary
""", ".gitattributes", lang="text")}
<p>Without <code>.gitattributes</code>, a teammate on Windows and you on Linux/macOS can produce diffs where every line \"changed\" only because of CRLF vs LF.</p>
{C(r"""
# Tag a release (annotated tag: has message, author, date)
git tag -a v1.0.0 -m "Bank simulator 1.0: accounts, ledger, events, domain exceptions"
git push origin v1.0.0           # tags are NOT pushed by a normal git push
git tag --list "v1.*"
git show v1.0.0

# Create a GitHub Release from the tag with auto-generated notes from merged PRs
gh release create v1.0.0 --title "v1.0.0" --generate-notes

# Semantic versioning: MAJOR.MINOR.PATCH
#   1.0.0 -> 1.0.1  fix
#   1.0.1 -> 1.1.0  feat (backwards compatible)
#   1.1.0 -> 2.0.0  breaking change

# Handy extras
git stash push -m "half-done export"   # shelve uncommitted work; git stash pop to restore
git cherry-pick 9f1c2ab                # copy one commit onto the current branch
git restore --staged Program.cs        # unstage
git commit --amend --no-edit           # add staged changes to the last (unpushed!) commit
""", lang="bash")}
''',
["Committing straight to main and pushing broken builds; protect main with branch rules and PRs.",
"Rebasing a shared branch, then force-pushing over teammates' work (use <code>--force-with-lease</code>, and only on your own branch).",
"Leaving conflict markers in a file because it was <code>git add</code>-ed without building.",
"Committing <code>bin/</code>, <code>obj/</code>, <code>.vs/</code> or secrets like <code>appsettings.Development.json</code> with real passwords.",
"Commit messages like \"changes\", \"wip\", \"final final\" — squash or reword them before the PR."],
("40 min", ["In a scratch repo, create the Case B history from section 2 (main moves after you branch). Merge it once with a merge commit and once (after <code>git reset --hard</code>) via rebase + fast-forward. Compare <code>git log --oneline --graph</code> outputs.",
"Create a deliberate conflict on one line of <code>Program.cs</code> from two branches, resolve it in VS Code's merge editor, and finish with <code>git rebase --continue</code>.",
"Make 4 messy commits, then use <code>git rebase -i</code> to turn them into 2 conventional commits, push, open a PR with <code>gh pr create</code>, squash-merge it and tag <code>v0.1.0</code>."]),
[("When does <code>git merge</code> create a merge commit?","When the target branch has commits the source doesn't (histories diverged). If the target is an ancestor of the source, Git fast-forwards instead, unless you pass <code>--no-ff</code>."),
("Why use <code>--force-with-lease</code> instead of <code>--force</code>?","It only overwrites the remote branch if it still points where you last saw it. If someone pushed in the meantime, the push is rejected instead of silently deleting their commits."),
("How do you recover a branch after a bad rebase?","Use <code>git reflog</code> to find the commit the branch pointed to before the rebase, then <code>git reset --hard &lt;that sha&gt;</code> (or create a new branch at it).")],
[("Basic","What is the difference between git merge and git rebase?","Merge combines two branches by creating a merge commit with two parents (or fast-forwarding), preserving history exactly. Rebase re-applies your commits on top of another base, producing new commits and a linear history. Merge is safe on shared branches; rebase rewrites history so use it only on commits that haven't been shared."),
("Basic","What is a fast-forward merge?","When the branch you merge into has no commits of its own since the branches split, Git just moves its pointer forward to the other branch's tip. No merge commit is created. <code>--no-ff</code> forces a merge commit anyway; <code>--ff-only</code> refuses if fast-forward isn't possible."),
("Basic","How do you resolve a merge conflict?","Run git status to see conflicted files, edit each to the correct final content and remove the &lt;&lt;&lt;&lt;&lt;&lt;&lt; / ======= / &gt;&gt;&gt;&gt;&gt;&gt;&gt; markers, build and run tests, git add the files, then git commit (merge) or git rebase --continue. git merge --abort / rebase --abort gives up and restores the previous state."),
("Intermediate","What does interactive rebase let you do and when would you use it?","<code>git rebase -i</code> lets you reorder, reword, squash, fix up, edit or drop commits on your branch. Use it before opening or updating a PR to turn noisy WIP commits into a few meaningful ones. Don't use it on commits already merged to a shared branch."),
("Intermediate","Squash merge, rebase merge or merge commit for PRs — which would you choose?","It's a team convention. Squash merge gives one commit per PR on main (easy to revert, clean log) but loses the individual commits. Rebase merge keeps each commit but linear. Merge commits keep the full true history and are best for long-lived branches. Many teams squash small feature PRs and protect main to require PRs and green CI."),
("Intermediate","What are .gitattributes used for in a .NET repository?","Normalising line endings (<code>* text=auto</code>, <code>eol=crlf</code> for .sln files), marking binaries so Git doesn't diff or merge them, and selecting diff drivers like <code>diff=csharp</code> for better hunk headers. It prevents whole-file CRLF/LF diffs between Windows and Linux developers.")])

# ================= DAY 2 =================
d2 = day(2, "TUE", "Unit testing preview: xUnit on the bank simulator",
"Add an xUnit test project to the Week 3 bank simulator and write facts, theories, exception tests and event tests in Arrange-Act-Assert style, then run them with dotnet test. Deep testing (mocks, fixtures, integration tests) comes in Week 39.",
[("Unit test","Code that runs a small piece of your code (one method or class) in isolation and checks the result automatically."),
("Test project","A separate project (e.g. <code>Bank.Tests</code>) that references the code under test and the test framework packages."),
("xUnit","The most widely used .NET test framework; ASP.NET Core itself is tested with it."),
("Test runner","The tool that discovers and executes tests: <code>dotnet test</code>, VS Test Explorer, Rider."),
("[Fact]","An attribute marking a test method that takes no parameters and is always true."),
("[Theory]","A parameterised test, run once per data row."),
("[InlineData]","Supplies one row of constant arguments to a theory."),
("[MemberData] / TheoryData&lt;T&gt;","Supplies theory rows from a static property; needed for types attributes can't hold, like <code>decimal</code>."),
("Arrange-Act-Assert (AAA)","Test layout: set up objects, perform one action, verify the outcome."),
("Assertion","A check that fails the test when false: <code>Assert.Equal</code>, <code>Assert.True</code>, <code>Assert.Throws</code>…"),
("System under test (SUT)","The class or method a test is exercising."),
("Test isolation","Each test sets up its own data and doesn't depend on other tests or on run order. xUnit creates a new instance of the test class for every test."),
("Code coverage","The percentage of lines/branches executed by tests; a hint about untested code, not a measure of quality."),
("Regression","A bug in behaviour that used to work. Tests catch regressions when you refactor.")],
["One test checks one behaviour; the name says which.",
"Tests use only the public API: <code>Deposit</code>, <code>Withdraw</code>, <code>Transfer</code> — not private fields.",
"Assert <code>expected</code> first, <code>actual</code> second: <code>Assert.Equal(1_500m, acc.Balance)</code>.",
"<code>Assert.Throws&lt;T&gt;</code> requires the <i>exact</i> type; <code>Assert.ThrowsAny&lt;T&gt;</code> accepts derived types.",
"Attributes can't contain <code>decimal</code> values, so use <code>int</code> parameters or <code>TheoryData</code> for money.",
"Tests that depend on <code>DateTime.Now</code> or random numbers are flaky; inject a clock (you did it with <code>IClock</code> in Week 2)."],
f'''
<h3>1. Add a test project to the bank solution</h3>
{C(r"""
cd Bank
dotnet new xunit -n Bank.Tests             # xUnit project: xunit, xunit.runner.visualstudio, Microsoft.NET.Test.Sdk, coverlet
dotnet sln add Bank.Tests
dotnet add Bank.Tests reference Bank.Core   # tests reference the library, never the console app
rm Bank.Tests/UnitTest1.cs
dotnet test                                 # builds everything and runs 0 tests — the wiring works
""", lang="bash")}
{C(r"""
Bank/
├─ Bank.sln
├─ Bank.Core/                (Week 3: Account, SavingsAccount, CurrentAccount, BankService, Exceptions/)
├─ Bank.App/
└─ Bank.Tests/
   ├─ Bank.Tests.csproj
   ├─ SavingsAccountTests.cs
   ├─ SavingsAccountRuleTests.cs
   ├─ AccountEventTests.cs
   └─ BankServiceTests.cs
""", lang="text")}
{C(r"""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="coverlet.collector" Version="6.0.2" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1" />
    <PackageReference Include="xunit" Version="2.9.2" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2" />
  </ItemGroup>
  <ItemGroup>
    <Using Include="Xunit" />          <!-- global using: no 'using Xunit;' needed in test files -->
  </ItemGroup>
  <ItemGroup>
    <ProjectReference Include="..\Bank.Core\Bank.Core.csproj" />
  </ItemGroup>
</Project>
""", "Bank.Tests/Bank.Tests.csproj (generated; versions vary with your SDK)", lang="xml")}
{tip("xUnit v3 is also available (<code>dotnet new install xunit.v3.templates</code>, then <code>dotnet new xunit3</code>). Everything on this page — Fact, Theory, InlineData, MemberData, Assert.Throws, Assert.Raises — works the same in v3.")}

<h3>2. Your first facts: Arrange-Act-Assert</h3>
{C(r"""
using Bank.Core;

namespace Bank.Tests;

public class SavingsAccountTests
{
    [Fact]
    public void Deposit_PositiveAmount_IncreasesBalance()
    {
        // Arrange
        var account = new SavingsAccount("Asha Rao");

        // Act
        account.Deposit(5_000m);

        // Assert
        Assert.Equal(5_000m, account.Balance);
    }

    [Fact]
    public void Deposit_RecordsOneCreditTransactionInLedger()
    {
        var account = new SavingsAccount("Asha Rao");

        account.Deposit(5_000m, "Salary");

        var tx = Assert.Single(account.Ledger);          // fails unless exactly one item; returns it
        Assert.Equal(TransactionType.Deposit, tx.Type);
        Assert.True(tx.IsCredit);
        Assert.Equal(5_000m, tx.BalanceAfter);
        Assert.Equal("Salary", tx.Note);
    }

    [Fact]
    public void ApplyMonthlyInterest_On12000At3Point5Percent_Credits35()
    {
        var account = new SavingsAccount("Asha Rao");
        account.Deposit(12_000m);

        decimal interest = account.ApplyMonthlyInterest();   // 12,000 × 0.035 / 12 = 35.00

        Assert.Equal(35.00m, interest);
        Assert.Equal(12_035.00m, account.Balance);
        Assert.Equal(TransactionType.Interest, account.Ledger[^1].Type);
    }
}
""", "Bank.Tests/SavingsAccountTests.cs (part 1)")}
{table(["Assertion","Checks"],[
["<code>Assert.Equal(expected, actual)</code>","Equality (uses Equals; collections compared element by element)"],
["<code>Assert.True(cond)</code> / <code>Assert.False(cond)</code>","A boolean condition"],
["<code>Assert.Null(x)</code> / <code>Assert.NotNull(x)</code>","Null-ness"],
["<code>Assert.Single(list)</code> / <code>Assert.Empty(list)</code>","Exactly one item (returned) / no items"],
["<code>Assert.Contains(item, list)</code>","Membership; overload with a predicate"],
["<code>Assert.Same(a, b)</code>","Same reference"],
["<code>Assert.IsType&lt;T&gt;(x)</code>","Exact runtime type (returns x cast to T)"],
["<code>Assert.Throws&lt;T&gt;(action)</code>","Exactly exception T is thrown (returns it)"],
["<code>Assert.Raises&lt;T&gt;(attach, detach, action)</code>","An event with args T is raised"]])}

<h3>3. Theories: one test, many rows</h3>
{C(r"""
public class SavingsAccountWithdrawTheories
{
    // Attribute arguments must be compile-time constants of primitive types: decimal is NOT allowed
    // ([InlineData(5000m)] is error CS0182). Use int parameters; they convert to decimal implicitly.
    [Theory]
    [InlineData(5_000, 4_000, 1_000)]     // leaves exactly the ₹1,000 minimum
    [InlineData(5_000, 1, 4_999)]
    [InlineData(10_000, 2_500, 7_500)]
    public void Withdraw_WithinAvailable_ReducesBalance(int opening, int amount, int expected)
    {
        var account = new SavingsAccount("Ravi Kumar");
        account.Deposit(opening);

        account.Withdraw(amount);

        Assert.Equal((decimal)expected, account.Balance);
    }

    // For real decimal values (paise), use strongly typed TheoryData + MemberData
    public static TheoryData<decimal, decimal> InterestCases => new()
    {
        { 12_000m,   35.00m },
        { 10_000m,   29.17m },     // 29.1666… rounded to 2 decimals
        { 1_234.56m,  3.60m }
    };

    [Theory]
    [MemberData(nameof(InterestCases))]
    public void ApplyMonthlyInterest_RoundsToTwoDecimals(decimal balance, decimal expectedInterest)
    {
        var account = new SavingsAccount("Ravi Kumar");
        account.Deposit(balance);

        Assert.Equal(expectedInterest, account.ApplyMonthlyInterest());
    }
}
""", "Bank.Tests/SavingsAccountTests.cs (part 2)")}
<p>Test Explorer and <code>dotnet test</code> show each row separately, e.g. <code>Withdraw_WithinAvailable_ReducesBalance(opening: 5000, amount: 1, expected: 4999)</code>, so a failing row is easy to spot.</p>
{warn("1,234.56 × 0.035 / 12 = 3.6008 → 3.60. Work expected values out by hand (or in a spreadsheet), never by copying what the code currently returns — otherwise the test just freezes today's bugs.", "Check your oracle")}

<h3>4. Testing exceptions</h3>
{C(r"""
using Bank.Core;
using Bank.Core.Exceptions;

namespace Bank.Tests;

public class SavingsAccountRuleTests
{
    [Fact]
    public void Withdraw_BelowMinimumBalance_ThrowsInsufficientFundsWithShortfall()
    {
        var account = new SavingsAccount("Meena Iyer");
        account.Deposit(5_000m);                         // available = 5,000 − 1,000 minimum = 4,000

        var ex = Assert.Throws<InsufficientFundsException>(() => account.Withdraw(4_500m));

        Assert.Equal(500m, ex.Shortfall);
        Assert.Equal(account.Number, ex.AccountNumber);
        Assert.Equal(5_000m, account.Balance);           // the failed withdrawal changed nothing
        Assert.Single(account.Ledger);                   // only the deposit was recorded
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-500)]
    public void Deposit_ZeroOrNegative_ThrowsArgumentOutOfRange(int amount)
    {
        var account = new SavingsAccount("Meena Iyer");

        var ex = Assert.Throws<ArgumentOutOfRangeException>(() => account.Deposit(amount));
        Assert.Equal("amount", ex.ParamName);
    }

    [Fact]
    public void Deposit_Negative_IsAnArgumentException()
    {
        var account = new SavingsAccount("Meena Iyer");

        // Throws<ArgumentException> would FAIL here: the actual type is the derived ArgumentOutOfRangeException
        Assert.ThrowsAny<ArgumentException>(() => account.Deposit(-1m));
    }

    [Fact]
    public void Withdraw_WhenFrozen_ThrowsAccountFrozenWithReason()
    {
        var account = new SavingsAccount("Meena Iyer");
        account.Deposit(10_000m);
        account.Freeze("KYC pending");

        var ex = Assert.Throws<AccountFrozenException>(() => account.Withdraw(100m));

        Assert.Equal("KYC pending", ex.Reason);
    }

    [Fact]
    public void Constructor_BlankHolder_Throws()
    {
        Assert.ThrowsAny<ArgumentException>(() => new SavingsAccount("   "));
    }
}
""", "Bank.Tests/SavingsAccountRuleTests.cs")}
{tip("Asynchronous code uses <code>await Assert.ThrowsAsync&lt;T&gt;(() =&gt; service.SaveAsync())</code> and the test method returns <code>async Task</code> — never <code>async void</code>. You'll use it on the Week 7 downloader.")}

<h3>5. Testing events</h3>
{C(r"""
using Bank.Core;

namespace Bank.Tests;

public class AccountEventTests
{
    [Fact]
    public void Withdraw_BelowThreshold_RaisesLowBalance()
    {
        var account = new SavingsAccount("Imran Shaikh");   // low-balance alert below ₹2,000
        account.Deposit(5_000m);

        var raised = Assert.Raises<LowBalanceEventArgs>(
            handler => account.LowBalance += handler,       // attach
            handler => account.LowBalance -= handler,       // detach
            () => account.Withdraw(3_500m));                // act

        Assert.Same(account, raised.Sender);
        Assert.Equal(1_500m, raised.Arguments.Balance);
        Assert.Equal(2_000m, raised.Arguments.Threshold);
    }

    [Fact]
    public void Withdraw_StayingAboveThreshold_DoesNotRaiseLowBalance()
    {
        var account = new SavingsAccount("Imran Shaikh");
        account.Deposit(5_000m);
        bool fired = false;
        account.LowBalance += (_, _) => fired = true;     // manual capture works for any event

        account.Withdraw(1_000m);                          // 4,000 left

        Assert.False(fired);
    }

    [Fact]
    public void Deposit_AtLargeTransactionLimit_RaisesLargeTransactionOnce()
    {
        var account = new CurrentAccount("Ugaav Labs");
        var captured = new List<LargeTransactionEventArgs>();
        account.LargeTransaction += (_, e) => captured.Add(e);

        account.Deposit(50_000m);                           // limit is inclusive (>= 50,000)
        account.Deposit(49_999m);                           // just under: no event

        var e = Assert.Single(captured);
        Assert.Equal(50_000m, e.Transaction.Amount);
        Assert.Equal(TransactionType.Deposit, e.Transaction.Type);
    }
}
""", "Bank.Tests/AccountEventTests.cs")}

<h3>6. Full test file: BankService, naming and running</h3>
{C(r"""
using Bank.Core;
using Bank.Core.Exceptions;

namespace Bank.Tests;

public class BankServiceTests
{
    // xUnit creates a NEW instance of this class for every test: these fields are fresh each time
    private readonly BankService _bank = new();
    private readonly SavingsAccount _savings;
    private readonly CurrentAccount _current;

    public BankServiceTests()                               // the constructor is the per-test "setup"
    {
        _savings = _bank.Open(new SavingsAccount("Neha Gupta"));
        _savings.Deposit(10_000m);
        _current = _bank.Open(new CurrentAccount("Neha Traders", overdraftLimit: 5_000m));
    }

    [Fact]
    public void Transfer_ValidAmount_MovesMoneyBetweenAccounts()
    {
        _bank.Transfer(_savings.Number, _current.Number, 4_000m);

        Assert.Equal(6_000m, _savings.Balance);
        Assert.Equal(4_000m, _current.Balance);
        Assert.Equal(TransactionType.TransferOut, _savings.Ledger[^1].Type);
        Assert.Equal(TransactionType.TransferIn, _current.Ledger[^1].Type);
    }

    [Fact]
    public void Transfer_InsufficientFunds_LeavesBothAccountsUnchanged()
    {
        var ex = Assert.Throws<InsufficientFundsException>(
            () => _bank.Transfer(_savings.Number, _current.Number, 9_500m));   // available is 9,000

        Assert.Equal(500m, ex.Shortfall);
        Assert.Equal(10_000m, _savings.Balance);
        Assert.Equal(0m, _current.Balance);
        Assert.Empty(_current.Ledger);                      // receiver was never credited
    }

    [Fact]
    public void Transfer_ToSameAccount_Throws()
    {
        Assert.Throws<InvalidOperationException>(
            () => _bank.Transfer(_savings.Number, _savings.Number.ToLowerInvariant(), 100m));
    }

    [Fact]
    public void Get_UnknownNumber_ThrowsAccountNotFound()
    {
        var ex = Assert.Throws<AccountNotFoundException>(() => _bank.Get("XX9999"));
        Assert.Equal("XX9999", ex.AccountNumber);
    }

    [Fact]
    public void Withdraw_CurrentAccount_CanUseOverdraftUpToLimit()
    {
        _current.Withdraw(5_000m);                          // 0 balance + 5,000 overdraft

        Assert.Equal(-5_000m, _current.Balance);
        Assert.Throws<InsufficientFundsException>(() => _current.Withdraw(1m));
    }

    [Fact]
    public void Withdraw_SecondWithdrawalOverDailyLimit_Throws()
    {
        _current.Deposit(2_00_000m);
        _current.Withdraw(60_000m);

        var ex = Assert.Throws<DailyLimitExceededException>(() => _current.Withdraw(50_000m));

        Assert.Equal(60_000m, ex.UsedToday);
        // ⚠ Uses DateTime.Today inside Account: this test can fail if run across midnight.
        //   The fix is to inject a clock (TimeProvider), as Wednesday's code review shows.
    }
}
""", "Bank.Tests/BankServiceTests.cs")}
<h4>Naming conventions</h4>
{table(["Style","Example","Notes"],[
["<code>Method_Scenario_ExpectedResult</code>","<code>Withdraw_BelowMinimumBalance_ThrowsInsufficientFunds</code>","Most common in .NET teams; used on this page"],
["<code>Should_Expected_When_Scenario</code>","<code>Should_RaiseLowBalance_When_BalanceDropsBelowThreshold</code>","Reads like a sentence"],
["Given/When/Then","<code>GivenFrozenAccount_WhenWithdrawing_ThenThrows</code>","BDD flavour"],
["Class per SUT","<code>SavingsAccountTests</code>, <code>BankServiceTests</code>","Mirror the production folder structure"]])}
{C(r"""
dotnet test                                              # build + run everything
dotnet test --filter "FullyQualifiedName~BankServiceTests"   # one class
dotnet test --filter "DisplayName~Transfer"              # name contains "Transfer"
dotnet test --logger "console;verbosity=detailed"        # show every test name
dotnet test --collect:"XPlat Code Coverage"              # coverage.cobertura.xml under TestResults/
dotnet watch test                                        # re-run on every save

# Passed!  - Failed:     0, Passed:    24, Skipped:     0, Total:    24, Duration: 64 ms - Bank.Tests.dll (net8.0)
""", lang="bash")}
<p>Skip a test temporarily with <code>[Fact(Skip = "Waiting for #42")]</code>; tag tests with <code>[Trait("Category", "Slow")]</code> and filter with <code>--filter "Category!=Slow"</code>.</p>
''',
["Several unrelated Acts and Asserts in one test, so the first failure hides the others and the name can't describe it.",
"Tests that share static state or depend on run order (xUnit runs test classes in parallel by default).",
"Writing <code>Assert.Equal(account.Balance, 1_500m)</code>: expected/actual swapped, so failure messages are misleading.",
"Using <code>Assert.Throws&lt;ArgumentException&gt;</code> when the code throws <code>ArgumentOutOfRangeException</code> (exact-type match fails).",
"Testing private methods via reflection instead of testing behaviour through the public API."],
("40 min", ["Add <code>Bank.Tests</code> to your Week 3 solution and get <code>SavingsAccountTests</code> and <code>BankServiceTests</code> above passing against your own code. Fix the code (not the tests) if a rule doesn't match the spec.",
"Write a <code>[Theory]</code> for <code>CurrentAccount</code>: overdraft limits 0, 5,000 and 20,000 — the largest allowed withdrawal from a zero balance succeeds and one rupee more throws.",
"Write tests for the Week 2/4 library: borrowing an item already on loan fails; a member with an overdue item can't borrow (use the <code>ManualClock</code> you already have)."]),
[("What's the difference between [Fact] and [Theory]?","A Fact has no parameters and runs once. A Theory has parameters and runs once per data row supplied by InlineData, MemberData or ClassData."),
("Why can't you write [InlineData(99.50m)]?","Attribute arguments must be compile-time constants of a limited set of types (primitives, string, Type, enums, arrays of those); decimal isn't one (CS0182). Use int/double parameters or TheoryData&lt;decimal&gt; with MemberData."),
("Where do you put setup code in xUnit?","In the test class constructor (runs before every test, because each test gets a new instance) and teardown in Dispose() by implementing IDisposable. Shared expensive setup goes in class fixtures (Week 39).")],
[("Basic","What is a unit test and why write them?","An automated check of a small unit of code in isolation. They catch regressions when you change code, document intended behaviour, give fast feedback (milliseconds), and push you towards decoupled designs because hard-to-test code is usually tightly coupled."),
("Basic","Explain the Arrange-Act-Assert pattern.","Arrange creates the objects and inputs; Act performs the single behaviour under test; Assert verifies the outcome. Keeping the three parts visually separate makes tests readable and keeps each test focused on one behaviour."),
("Basic","How do you test that a method throws an exception in xUnit?","<code>var ex = Assert.Throws&lt;InsufficientFundsException&gt;(() =&gt; account.Withdraw(4_500m));</code> then assert on the exception's properties. Throws requires the exact type; ThrowsAny accepts subclasses; ThrowsAsync for async code."),
("Intermediate","How do you test that an event was raised?","Use <code>Assert.Raises&lt;TEventArgs&gt;(attach, detach, act)</code>, which returns the sender and arguments, or subscribe a lambda that records calls into a list/flag and assert on it. Also test the negative case: the event is not raised when the condition isn't met."),
("Intermediate","What makes a test flaky and how do you fix it?","Dependence on things that vary between runs: current time, random numbers, shared static state, test order, the file system or network. Fix by injecting abstractions (IClock, a seeded Random, TimeProvider in .NET 8), giving each test its own data, and keeping unit tests in memory."),
("Intermediate","Is 100% code coverage a good goal?","Not by itself. Coverage shows which lines ran, not whether the assertions are meaningful. Aim for high coverage of business rules and edge cases (limits, rounding, failure paths) and accept lower coverage for trivial code like DTOs and Program.cs.")])

# ================= DAY 3 =================
d3 = day(3, "WED", "Code review of your Phase 1 repos: checklist, smells and analyzers",
"Review your own Phase 1 code the way a senior developer would, fix the most common smells, let analyzers catch the rest automatically, and refactor your weakest repository.",
[("Code review","Reading a change (or a whole codebase) to find bugs, design problems and unclear code before it reaches users."),
("Code smell","A surface sign of a deeper problem: long methods, magic numbers, duplicated logic. Not a bug yet, but where bugs grow."),
("Magic number","An unexplained literal in code, e.g. <code>0.18m</code> or <code>1000</code>; replace with a named constant or configuration."),
("Single Responsibility (SRP)","A class or method should have one reason to change (Week 9)."),
("Primitive obsession","Using <code>string</code>/<code>decimal</code> for domain concepts (PIN codes, money, emails) instead of small types that validate themselves."),
("Swallowed exception","A <code>catch</code> that hides a failure without handling or logging it."),
("Analyzer","A Roslyn component that inspects code at compile time and reports diagnostics (CA…, IDE…, CS…)."),
(".editorconfig","A file of style and analyzer settings that IDEs and the compiler both read, so the whole team gets the same rules."),
("Diagnostic severity","How seriously a rule is reported: none, silent, suggestion, warning, error."),
("TreatWarningsAsErrors","An MSBuild property that fails the build on any warning, so warnings can't pile up."),
("Directory.Build.props","An MSBuild file automatically imported by every project below its folder; the place for shared settings."),
("dotnet format","CLI tool that applies .editorconfig style and analyzer fixes to the whole solution."),
("Characterisation test","A test written before refactoring to pin down what the code currently does.")],
["Review in passes: correctness first, then design, then naming and style.",
"Let tools handle style (formatting, using order); spend human attention on logic and design.",
"Nullable reference types + warnings-as-errors remove a whole class of NullReferenceException bugs.",
"Every smell fix should keep behaviour the same — prove it with tests from yesterday.",
"Refactor in small commits (<code>refactor:</code>), one smell per commit, build and test after each.",
"Write review comments about the code, never the person: \"this method\" not \"you\"."],
f'''
<h3>1. The checklist</h3>
<p>Open each Phase 1 repo (Toolkit, City Library, Bank, Grade Analyzer, Expense Tracker, Downloader, Parking Lot) and walk this list. Note every finding as a GitHub issue in that repo, labelled <code>refactor</code>.</p>
{table(["Area","Ask","Red flags"],[
["Naming","Can I tell what it does without reading the body?","<code>Process()</code>, <code>data2</code>, <code>Helper</code>, <code>Manager</code>, abbreviations, Hungarian notation"],
["SRP / size","Does this class/method have one reason to change?","Methods over ~30 lines, classes mixing console I/O + rules + file access, <code>Program.cs</code> with 400 lines"],
["Magic numbers/strings","Is every literal explained?","<code>0.18m</code>, <code>1000</code>, <code>\"SB\"</code>, repeated file paths"],
["Exception handling","Are failures handled where something useful can be done?","<code>catch { }</code>, <code>catch (Exception)</code> that just prints, <code>throw ex;</code>, exceptions for normal flow"],
["Null handling","Can anything be null here? Does the compiler know?","Nullable disabled, <code>!</code> sprinkled everywhere, missing guard clauses on public methods"],
["Async correctness","Is every Task awaited, every token passed?","<code>async void</code>, <code>.Result</code>/<code>.Wait()</code>, missing CancellationToken, un-awaited calls (CS4014)"],
["Collection choice","Does the data structure match the access pattern?","<code>List.Contains</code> in a loop, <code>RemoveAt(0)</code> as a queue, returning mutable <code>List&lt;T&gt;</code> from public APIs"],
["Resources","Is everything disposable disposed?","<code>new StreamReader(...)</code> without <code>using</code>, new <code>HttpClient</code> per request"],
["Testability","Can I test the rules without a console, a file or the clock?","<code>DateTime.Now</code>, <code>Console.ReadLine</code> or <code>File.*</code> inside domain classes"],
["Tests","Do tests exist for the business rules and edge cases?","No test project; tests with no assertions; only happy paths"],
["README","Could a recruiter run it in 2 minutes?","No README, no run command, no screenshots, outdated feature list"]])}

<h3>2. Before/after: magic numbers, primitive obsession and hidden time</h3>
{C(r"""
// ❌ BEFORE (Expense Tracker, Week 6)
public decimal Total(List<Expense> items)
{
    decimal t = 0;
    foreach (var e in items)
    {
        if (e.Cat == "Food" && e.Date.Month == DateTime.Now.Month) t += e.Amt * 1.05m;
        else if (e.Cat == "Electronics") t += e.Amt * 1.18m;
        else t += e.Amt;
    }
    return Math.Round(t, 2);
}
""", "ExpenseCalculator.cs (before)")}
{C(r"""
// ✓ AFTER — names, constants, enum instead of strings, time injected, rule in one place
public enum ExpenseCategory { Food, Electronics, Travel, Other }

public static class GstRates
{
    public const decimal Food = 0.05m;
    public const decimal Electronics = 0.18m;

    public static decimal For(ExpenseCategory category) => category switch
    {
        ExpenseCategory.Food        => Food,
        ExpenseCategory.Electronics => Electronics,
        _                           => 0m
    };
}

public sealed class ExpenseCalculator(TimeProvider time)     // TimeProvider: built into .NET 8
{
    public decimal MonthTotalIncludingGst(IEnumerable<Expense> expenses)
    {
        var today = DateOnly.FromDateTime(time.GetLocalNow().DateTime);
        decimal total = expenses
            .Where(e => e.Date.Year == today.Year && e.Date.Month == today.Month)
            .Sum(e => e.Amount * (1 + GstRates.For(e.Category)));
        return Math.Round(total, 2);
    }
}

public sealed record Expense(DateOnly Date, ExpenseCategory Category, decimal Amount, string Description);

// Production: new ExpenseCalculator(TimeProvider.System)
// Tests:      a fake TimeProvider fixed at a known date (Microsoft.Extensions.TimeProvider.Testing)
""", "ExpenseCalculator.cs (after)")}
<p>Notice the <i>before</i> version also had a real bug a review should catch: the month check compared months but not years, and only applied to food, so electronics from last year were counted in this month's total.</p>


<h3>3. Before/after: exceptions, nulls and async</h3>
{C(r"""
// ❌ BEFORE (Downloader, Week 7)
public async void Download(string url)                        // async void: caller can't await or catch
{
    try
    {
        var client = new HttpClient();                         // new client per call: socket exhaustion
        var bytes = client.GetByteArrayAsync(url).Result;      // blocks a thread; can deadlock with a sync context
        File.WriteAllBytes(GetName(url), bytes);
    }
    catch (Exception ex) { Console.WriteLine("error"); }      // swallows everything, loses the cause
}
string GetName(string url) => url.Split('/').Last();          // null/empty url → crash or "" filename
""", "Downloader.cs (before)")}
{C(r"""
// ✓ AFTER
public sealed class FileDownloader(HttpClient http, string targetFolder)
{
    public async Task<string> DownloadAsync(Uri url, CancellationToken ct = default)
    {
        ArgumentNullException.ThrowIfNull(url);

        string fileName = Path.GetFileName(url.LocalPath);
        if (string.IsNullOrWhiteSpace(fileName))
            throw new ArgumentException($"URL has no file name: {url}", nameof(url));

        string path = Path.Combine(targetFolder, fileName);
        using var response = await http.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, ct);
        response.EnsureSuccessStatusCode();                    // non-2xx → HttpRequestException

        await using var file = File.Create(path);
        await response.Content.CopyToAsync(file, ct);           // streams; no whole file in memory
        return path;
    }
}

// Caller decides what a failure means — and only catches what it can handle
try
{
    string saved = await downloader.DownloadAsync(new Uri("https://example.com/reports/gst-2026.pdf"), cts.Token);
    Console.WriteLine($"Saved {saved}");
}
catch (HttpRequestException ex)
{
    Console.WriteLine($"Download failed ({ex.StatusCode}): {ex.Message}");
}
catch (OperationCanceledException)
{
    Console.WriteLine("Cancelled.");
}
""", "FileDownloader.cs (after)")}

<h3>4. Before/after: SRP and collection choice</h3>
{C(r"""
// ❌ BEFORE (Grade Analyzer, Week 5): one method reads the file, validates, calculates and prints
public static void Run(string path)
{
    var lines = File.ReadAllLines(path);
    var students = new List<string>();
    foreach (var l in lines.Skip(1))
    {
        var p = l.Split(',');
        if (!students.Contains(p[0])) students.Add(p[0]);      // O(n) inside a loop → O(n²)
        // ... 60 more lines: parsing marks, averages, grade bands, Console.WriteLine ...
    }
}
""", "GradeReport.cs (before)")}
{C(r"""
// ✓ AFTER: each piece has one job and can be tested on its own
public sealed record StudentMark(string RollNo, string Subject, int Marks);

public static class MarksCsvParser                                   // job: text → records
{
    public static IReadOnlyList<StudentMark> Parse(IEnumerable<string> lines) =>
        lines.Skip(1)
             .Where(l => !string.IsNullOrWhiteSpace(l))
             .Select(l => l.Split(','))
             .Select(p => new StudentMark(p[0].Trim(), p[1].Trim(), int.Parse(p[2])))
             .ToList();
}

public static class GradeBands                                       // job: the grading rule
{
    public static char For(double average) => average switch
    {
        >= 90 => 'A',
        >= 75 => 'B',
        >= 60 => 'C',
        >= 40 => 'D',
        _     => 'F'
    };
}

public static class GradeReport                                      // job: aggregate
{
    public static IReadOnlyList<(string RollNo, double Average, char Grade)> Build(IEnumerable<StudentMark> marks) =>
        marks.GroupBy(m => m.RollNo)                                 // replaces the List.Contains de-dup
             .Select(g => (g.Key, Avg: g.Average(m => m.Marks)))
             .Select(x => (x.Key, x.Avg, GradeBands.For(x.Avg)))
             .OrderByDescending(x => x.Avg)
             .ToList();
}

// Program.cs: the only place that touches the file system and the console
var report = GradeReport.Build(MarksCsvParser.Parse(File.ReadLines("marks.csv")));
foreach (var (roll, avg, grade) in report)
    Console.WriteLine($"{roll,-8} {avg,6:F1} {grade}");
""", "GradeReport.cs (after)")}

<h3>5. Let analyzers enforce the boring parts</h3>
{C(r"""
<Project>
  <!-- Directory.Build.props at the solution root: applies to EVERY project below it.
       Remove TargetFramework/Nullable/ImplicitUsings from each .csproj once they live here. -->
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AnalysisLevel>latest-recommended</AnalysisLevel>      <!-- turn on the recommended CA rule set -->
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild> <!-- IDE style rules also run in dotnet build / CI -->
    <GenerateDocumentationFile>true</GenerateDocumentationFile> <!-- needed for IDE0005 (unused usings) in builds -->
    <NoWarn>$(NoWarn);CS1591</NoWarn>                       <!-- ...but don't demand XML docs on everything -->
  </PropertyGroup>
</Project>
""", "Directory.Build.props", lang="xml")}
{C(r"""
# .editorconfig at the solution root
root = true

[*]
indent_style = space
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.cs]
indent_size = 4
csharp_style_namespace_declarations = file_scoped:warning
csharp_style_var_when_type_is_apparent = true:suggestion
dotnet_sort_system_directives_first = true

# Private fields: _camelCase
dotnet_naming_rule.private_fields_underscore.symbols  = private_fields
dotnet_naming_rule.private_fields_underscore.style    = underscore_camel
dotnet_naming_rule.private_fields_underscore.severity = warning
dotnet_naming_symbols.private_fields.applicable_kinds = field
dotnet_naming_symbols.private_fields.applicable_accessibilities = private
dotnet_naming_style.underscore_camel.required_prefix = _
dotnet_naming_style.underscore_camel.capitalization  = camel_case

# Rule severities (keep comments on their own lines in .editorconfig)
# The ':warning' suffix above and the naming-rule severity are honoured only in the IDE.
# dotnet build / CI enforce IDE rules only through dotnet_diagnostic lines like these:
# IDE0161 file-scoped namespace; IDE1006 naming rules
dotnet_diagnostic.IDE0161.severity = warning
dotnet_diagnostic.IDE1006.severity = warning
# IDE0005 unnecessary using; IDE0044 field can be readonly
dotnet_diagnostic.IDE0005.severity = warning
dotnet_diagnostic.IDE0044.severity = warning
# CA1822 member can be static; CA2016 forward the CancellationToken
dotnet_diagnostic.CA1822.severity = suggestion
dotnet_diagnostic.CA2016.severity = warning
# CA1305 IFormatProvider: too noisy for console learning projects
dotnet_diagnostic.CA1305.severity = none

[*Tests.cs]
# CA1707: allow underscores in test method names
dotnet_diagnostic.CA1707.severity = none
""", ".editorconfig", lang="ini")}
{C(r"""
dotnet new editorconfig                    # generates a full .editorconfig with .NET defaults to edit
dotnet format                              # apply style + fixable analyzer suggestions to the whole solution
dotnet format --verify-no-changes          # CI mode: exit code 2 if anything would change
dotnet build -warnaserror                  # one-off: see what TreatWarningsAsErrors would break
""", lang="bash")}
{table(["Diagnostic","Meaning","Typical fix"],[
["CS8602 / CS8618","Possible null dereference / non-nullable property not initialised","Guard, <code>required</code>, or make it nullable honestly"],
["CS4014","Call to async method not awaited","<code>await</code> it (or assign and await later)"],
["CA2016","CancellationToken not forwarded","Pass <code>ct</code> to the inner async call"],
["CA1822","Member doesn't use instance data","Mark <code>static</code>"],
["CA1062","Public method doesn't validate a reference argument","<code>ArgumentNullException.ThrowIfNull(x)</code>"],
["IDE0044","Private field never reassigned","Add <code>readonly</code>"],
["IDE0005","Unused using directive","Delete it (<code>dotnet format</code> does)"],
["CA2000","Disposable not disposed","<code>using var</code>"]])}
{tip("Turning on warnings-as-errors in an old repo can produce 200 errors. Do it on a branch, fix category by category (nullable first), commit each category separately, then merge.")}

<h3>6. Refactor the worst repo — a safe process</h3>
{C(r"""
git switch -c refactor/expense-tracker-review
# 1. Pin current behaviour BEFORE changing anything
dotnet new xunit -n Expense.Tests && dotnet sln add Expense.Tests
dotnet add Expense.Tests reference Expense.Core
#    write characterisation tests for totals, CSV import and category summaries — they must pass now
dotnet test

# 2. One smell per commit; build + test after each
git commit -am "refactor(expense): replace category strings with ExpenseCategory enum"
git commit -am "refactor(expense): extract GstRates and remove magic numbers"
git commit -am "refactor(expense): inject TimeProvider into ExpenseCalculator"
git commit -am "fix(expense): month total ignored the year"    # bugs found along the way get their own commit
git commit -am "build: enable nullable and TreatWarningsAsErrors"

# 3. Open a PR to yourself and review the diff on GitHub as if a colleague wrote it
git push -u origin refactor/expense-tracker-review
gh pr create --fill
""", lang="bash")}
<h4>Writing review comments (for your own PR and, later, colleagues')</h4>
{table(["Prefix","Meaning","Example"],[
["<b>issue:</b>","Must fix before merge","issue: <code>Transfer</code> credits before debiting, so a failed debit leaves money in the target account."],
["<b>suggestion:</b>","Better way, author decides","suggestion: <code>HashSet&lt;string&gt;</code> would make this lookup O(1)."],
["<b>question:</b>","Reviewer doesn't understand","question: why is the grace period 10 minutes here but 15 in the README?"],
["<b>nit:</b>","Tiny, non-blocking","nit: <code>amt</code> → <code>amount</code>."],
["<b>praise:</b>","Call out good work","praise: nice use of TheoryData for the GST cases."]])}
''',
["Reviewing formatting by eye instead of letting <code>dotnet format</code> and .editorconfig enforce it.",
"Refactoring and changing behaviour in the same commit, so neither can be reviewed or reverted cleanly.",
"Suppressing warnings with <code>#pragma warning disable</code> or <code>!</code> instead of fixing the cause.",
"Catching <code>Exception</code> to \"make it not crash\" — the bug is now silent instead of loud.",
"Starting a refactor without tests and discovering a week later that totals changed."],
("40 min", ["Run the checklist on two Phase 1 repos and create at least 5 GitHub issues per repo, each naming the file, the smell and the proposed fix.",
"Add the <code>Directory.Build.props</code> and <code>.editorconfig</code> above to the Bank solution, run <code>dotnet build</code>, and fix every warning until it builds clean with TreatWarningsAsErrors.",
"Pick the repo with the most issues, write 3 characterisation tests, then fix 3 smells in 3 separate <code>refactor:</code> commits and open a PR to yourself."]),
[("What's the difference between a code smell and a bug?","A bug is incorrect behaviour now. A smell is a structural sign (long method, magic numbers, duplicated rules) that makes bugs likely and changes risky, even though the code currently works."),
("What does EnforceCodeStyleInBuild do?","It runs the IDE code-style analyzers (IDExxxx rules configured in .editorconfig) during dotnet build, so CI fails on style violations, not just the editor showing squiggles."),
("Why write characterisation tests before refactoring?","They capture current behaviour so you can prove the refactor didn't change it. If one fails after a refactor step, you know exactly which step broke it.")],
[("Basic","What do you look for when reviewing a pull request?","Correctness first (logic, edge cases, error handling, null and async issues), then design (responsibilities, coupling, naming, duplication), then tests (do they cover the change and its failure paths), security (secrets, input validation), and finally readability. Style should be automated, not debated."),
("Basic","What is a magic number and how do you fix it?","An unexplained literal like 0.18m or 1000 in logic. Replace it with a named constant, enum or configuration value (e.g. <code>GstRates.Electronics</code>, <code>SavingsAccount.MinimumBalance</code>) so its meaning is clear and it changes in one place."),
("Basic","Why is catch (Exception) { } dangerous?","It hides every failure, including bugs like NullReferenceException, leaving the program in an unknown state with no trace. Catch only exceptions you can handle meaningfully, log the rest and let them propagate."),
("Intermediate","How do you enforce coding standards across a team?","An .editorconfig committed to the repo for style and analyzer severities; Directory.Build.props for shared settings like Nullable, AnalysisLevel and TreatWarningsAsErrors; EnforceCodeStyleInBuild plus <code>dotnet format --verify-no-changes</code> in CI; and branch protection requiring green CI and a review."),
("Intermediate","Why is async void problematic and where is it acceptable?","The caller gets no Task, so it can't await completion or observe exceptions; an exception in async void is raised on the synchronization context and typically crashes the process. It's acceptable only for event handlers, whose signature requires void."),
("Intermediate","What is primitive obsession? Give a fix.","Representing domain concepts with raw primitives (string PIN code, decimal amount with a separate currency string). Fix with small types that validate themselves, e.g. <code>readonly record struct PinCode</code> that only accepts six digits, or a Money type that carries the currency.")])

# ================= DAY 4 =================
d4 = day(4, "THU", "Timed exercise: rebuild the parking lot system from scratch",
"Prove the Phase 1 skills are yours: rebuild the Week 9 parking lot in two hours with the notes closed, then score yourself honestly and compare with the reference design.",
[("Low-level design (LLD)","Designing the classes, their responsibilities and interactions for one feature or system; a standard interview round."),
("Requirements clarification","The first minutes of an LLD: asking what's in and out of scope before drawing classes."),
("Entity","An object with identity that changes over time: a slot, a ticket (closed on exit)."),
("Value object","An immutable object defined by its values: a vehicle (registration number + type)."),
("Allocation strategy","The rule for choosing which free slot a vehicle gets: nearest, smallest fitting, by level."),
("Pricing strategy","An interchangeable fee rule behind an interface (Strategy pattern, Week 9)."),
("Grace period","Free minutes after entry, e.g. 10 minutes to drop someone off."),
("Ceiling billing","Charging every started hour as a full hour: 61 minutes = 2 hours."),
("Time box","A fixed amount of time for a task; when it ends you stop and move on."),
("Rubric","A scoring table that turns \"I think it went fine\" into numbers you can track."),
("Reference solution","A model answer to compare against <i>after</i> attempting, not to read before.")],
["Close every tab, the old repo and these notes until the timer ends. Only the .NET docs are allowed.",
"Spend the first 10 minutes on requirements and a class list on paper; don't type code yet.",
"Make it work in the console first; extensibility second; polish last.",
"Write at least 3 tests — yesterday's xUnit skills are part of the score.",
"When a time box ends, commit what you have and move on.",
"Score yourself straight after; the gaps you find are Sunday's revision list."],
f'''
<h3>1. Requirements recap (read once, then close the page)</h3>
<ul>
<li>The lot has several <b>levels</b>; each level has slots of size <b>Small</b>, <b>Medium</b> and <b>Large</b>.</li>
<li>Vehicles: <b>Bike</b> needs Small, <b>Car</b> needs Medium, <b>Truck</b> needs Large. A vehicle may use a <i>bigger</i> slot if its own size is full, never a smaller one.</li>
<li>Levels are numbered from 1; slots are created from a layout (small/medium/large counts per level) and get ids like <code>L1-S01</code>, <code>L1-M03</code>, <code>L2-L06</code>.</li>
<li>Allocate the <b>smallest fitting slot</b>, lowest level first.</li>
<li>Registration numbers are normalised (spaces and dashes removed, upper case) and validated. The same vehicle can't be parked twice.</li>
<li>Parking issues a <b>ticket</b> with a sequential id (<code>T0001</code>), vehicle, slot and entry time.</li>
<li>Exit takes the ticket id, frees the slot, and returns the closed ticket with exit time and amount.</li>
<li><b>Fees (₹):</b> first 10 minutes free; after that every started hour is billed (minimum 1 hour) at Bike ₹10, Car ₹40, Truck ₹100 per hour. A car parked 2h30m pays 3 × ₹40 = ₹120.</li>
<li>Show <b>availability</b> per level and slot size, and announce when a vehicle type's slots become full or free again.</li>
<li>Pricing must be swappable (a weekend or monthly-pass rule later) without editing the lot class.</li>
<li>Time must be controllable in tests.</li>
</ul>
{C(r"""
mkdir parking-rebuild && cd parking-rebuild
git init
dotnet new sln -n ParkingLot
dotnet new classlib -n ParkingLot.Core
dotnet new console  -n ParkingLot.App
dotnet new xunit    -n ParkingLot.Tests
dotnet sln add ParkingLot.Core ParkingLot.App ParkingLot.Tests
dotnet add ParkingLot.App   reference ParkingLot.Core
dotnet add ParkingLot.Tests reference ParkingLot.Core
rm ParkingLot.Core/Class1.cs ParkingLot.Tests/UnitTest1.cs
dotnet new gitignore
git add . && git commit -m "chore: scaffold parking rebuild"
# start the 2-hour timer NOW
""", lang="bash")}

<h3>2. Design decisions to make (write one line for each before coding)</h3>
{table(["#","Decision","Options","What a good answer considers"],[
["1","How to model vehicle kinds","Enum + record vs class hierarchy (Car : Vehicle)","Behaviour differs only by size and price → an enum is enough; a hierarchy adds nothing yet"],
["2","How slot sizes compare","Enum with ordered values vs a lookup table","<code>Small = 1, Medium = 2, Large = 3</code> lets you write <code>slot.Size &gt;= required</code>"],
["3","Who owns allocation","ParkingLotService, Level, or a separate IAllocationStrategy","Start in ParkingLotService; extract a strategy only if a second rule appears"],
["4","How fees are calculated","Inside the service vs <code>IPricingStrategy</code>","Requirement says swappable → Strategy behind an interface (OCP, DIP)"],
["5","How time is obtained","<code>DateTime.Now</code> vs injected clock","Inject your own <code>IClock</code> (Week 9) and use <code>ManualClock</code> in tests; .NET 8's <code>TimeProvider</code> is the built-in alternative"],
["6","Failure reporting","Exceptions vs Result&lt;T&gt;","\"Lot full\" and \"already parked\" are expected outcomes → Result; programmer errors (null) → exceptions"],
["7","Lookups","List scans vs Dictionary/HashSet","Open tickets by id and by vehicle number: two <code>Dictionary&lt;string, Ticket&gt;</code> with OrdinalIgnoreCase; slots by id"],
["8","Mutability","Mutable entities vs immutable records","Slot occupancy and the ticket's exit time change (entities, classes); Vehicle never changes (record)"],
["9","Encapsulation","Public setters vs internal methods","Only ParkingLotService may assign/release a slot or close a ticket → <code>internal</code> methods, read-only public state"],
["10","Money type","double vs decimal","decimal, always"]])}

<h3>3. Milestones and time boxes (2 hours)</h3>
{table(["Time","Milestone","Done when"],[
["0:00–0:10","Requirements, nouns → classes, decisions table above","Paper list of ~7 types and their responsibilities"],
["0:10–0:30","Model: enums, Vehicle, ParkingSlot, Level, Ticket, slot factory","<code>dotnet build</code> succeeds; commit <code>feat: domain model</code>"],
["0:30–0:55","ParkingLotService.Park: allocation + duplicates + lot-full event","Console demo parks a car, bike and truck; lot-full case handled"],
["0:55–1:15","Pricing strategy + Exit","Exit returns the closed ticket: 2h30m car = ₹120; commit"],
["1:15–1:35","Tests (at least 3) with <code>ManualClock</code>","<code>dotnet test</code> green"],
["1:35–1:50","Console app menu: enter, exit, availability","Can run a full session by hand"],
["1:50–2:00","README stub, final commit, stop","Timer ends — no \"just five more minutes\""]])}

<h3>4. Self-scoring rubric (out of 30)</h3>
{table(["Area","0","1","2","3"],[
["Requirements covered","Under half","Most, with bugs","All, minor bugs","All, correct"],
["Fee rule correctness","Wrong","Right for one vehicle","Right except grace/ceiling edge","All cases right, decimal"],
["Allocation","Any slot","Exact size only","Smallest fitting","Smallest fitting, lowest level, no double parking"],
["Responsibilities (SRP)","Everything in Program.cs","God ParkingLotService","Clear classes, some leakage","Each class one job; console only in App"],
["Extensibility (OCP/DIP)","Fees hard-coded in if/else","Switch in lot","Interface but newed inside","Interface injected via constructor"],
["Encapsulation","Public setters everywhere","Some","Mostly private/internal","State changes only through methods"],
["Testability","Uses DateTime.Now","—","Clock injected","Clock injected and used in tests"],
["Tests","None","1 test","3 tests happy path","3+ incl. failure path and fee edge"],
["Naming & readability","Cryptic","Mixed","Good","Reads like the requirements"],
["Git hygiene","One commit","Few, vague","Several, clear","Small conventional commits per milestone"]])}
<p><b>25–30:</b> Phase 1 exit passed. <b>18–24:</b> pass; redo the weakest two rows next weekend. <b>Below 18:</b> repeat the exercise on a buffer day after re-reading Weeks 2 and 9.</p>

<h3>5. Reference solution (open only after the timer)</h3>
<p>A condensed version of your Week 9 Sunday design: same names, same fee rule, same Strategy, Factory and Observer. Week 9 splits these types into <code>Models/</code>, <code>Pricing/</code>, <code>Setup/</code> and <code>Services/</code> folders and namespaces; here they share one namespace and the extras (EV slots, flat and peak pricing, the console menu) are left out. Compare <i>decisions</i>, not line counts.</p>
{C(r"""
using System.Text.RegularExpressions;

namespace ParkingLot.Core;

public readonly record struct Result<T>(bool Success, T? Value, string? Error)
{
    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);
}

public interface IClock { DateTime Now { get; } }

public sealed class SystemClock : IClock { public DateTime Now => DateTime.Now; }

public sealed class ManualClock(DateTime start) : IClock           // demos and tests: time moves only when told
{
    public DateTime Now { get; private set; } = start;

    public void Advance(TimeSpan by)
    {
        if (by < TimeSpan.Zero) throw new ArgumentOutOfRangeException(nameof(by), "Time can't go backwards");
        Now += by;
    }
}

public enum VehicleType { Bike, Car, Truck }

public enum SlotSize { Small = 1, Medium = 2, Large = 3 }          // ordered: bigger value = bigger slot

public sealed record Vehicle
{
    // Simplified Indian format: state code, RTO number, 0–3 series letters, 4 digits (KA01AB1234)
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
        (Number, Type) = (normalised, type);
    }

    public static string Normalise(string number) =>
        number.Replace(" ", "").Replace("-", "").ToUpperInvariant();

    public override string ToString() => $"{Type} {Number}";
}
""", "ParkingLot.Core/Basics.cs")}
{C(r"""
namespace ParkingLot.Core;

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
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(level);          // levels are numbered from 1
        (Id, Level, Size) = (id, level, size);
    }

    public static SlotSize RequiredSize(VehicleType type) => type switch
    {
        VehicleType.Bike  => SlotSize.Small,
        VehicleType.Car   => SlotSize.Medium,
        VehicleType.Truck => SlotSize.Large,
        _ => throw new ArgumentOutOfRangeException(nameof(type))
    };

    public bool CanFit(VehicleType type) => Size >= RequiredSize(type);  // own size or bigger

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

public class Level
{
    public int Number { get; }
    public IReadOnlyList<ParkingSlot> Slots { get; }

    public Level(int number, IEnumerable<ParkingSlot> slots)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(number);
        var list = slots.ToList();
        if (list.Count == 0) throw new ArgumentException($"Level {number} has no slots", nameof(slots));
        (Number, Slots) = (number, list.AsReadOnly());
    }
}

public class Ticket                                                  // an entity: it is closed on exit
{
    public string Id { get; }
    public Vehicle Vehicle { get; }
    public string SlotId { get; }
    public DateTime EntryTime { get; }
    public DateTime? ExitTime { get; private set; }
    public decimal? Amount { get; private set; }

    internal Ticket(string id, Vehicle vehicle, ParkingSlot slot, DateTime entryTime) =>
        (Id, Vehicle, SlotId, EntryTime) = (id, vehicle, slot.Id, entryTime);

    public TimeSpan Duration(DateTime now) => (ExitTime ?? now) - EntryTime;

    internal void Close(DateTime exitTime, decimal amount)
    {
        if (ExitTime is not null) throw new InvalidOperationException($"Ticket {Id} is already closed");
        (ExitTime, Amount) = (exitTime, amount);
    }
}

public sealed record SlotCount(SlotSize Size, int Free, int Total);
public sealed record LevelAvailability(int Level, IReadOnlyList<SlotCount> Counts);
""", "ParkingLot.Core/Models.cs")}
{C(r"""
namespace ParkingLot.Core;

// ---- Strategy: how a stay is priced ----
public interface IPricingStrategy
{
    string Name { get; }
    decimal Calculate(VehicleType type, DateTime entry, DateTime exit);
}

public sealed class HourlyPricing : IPricingStrategy
{
    private readonly IReadOnlyDictionary<VehicleType, decimal> _ratePerHour;
    private readonly TimeSpan _grace;

    public HourlyPricing(IReadOnlyDictionary<VehicleType, decimal> ratePerHour, TimeSpan? grace = null)
    {
        if (Enum.GetValues<VehicleType>().Any(t => !ratePerHour.ContainsKey(t)))
            throw new ArgumentException("Every vehicle type needs a rate", nameof(ratePerHour));
        _ratePerHour = ratePerHour;
        _grace = grace ?? TimeSpan.FromMinutes(10);
    }

    public string Name => "Hourly";

    public decimal Calculate(VehicleType type, DateTime entry, DateTime exit)
    {
        if (exit < entry) throw new ArgumentException("Exit can't be before entry", nameof(exit));
        TimeSpan length = exit - entry;
        if (length <= _grace) return 0m;                              // grace period
        int hours = (int)Math.Ceiling(length.TotalHours);              // every started hour; at least 1
        return hours * _ratePerHour[type];                             // car 2h30m → 3 × ₹40 = ₹120
    }
}

// ---- Factory: the one place that knows the slot id format ----
public sealed record LevelConfig(int Level, int Small, int Medium, int Large);

public interface ISlotFactory
{
    ParkingSlot Create(int level, SlotSize size, int position);
}

public sealed class StandardSlotFactory : ISlotFactory
{
    public ParkingSlot Create(int level, SlotSize size, int position)
    {
        char code = size switch { SlotSize.Small => 'S', SlotSize.Medium => 'M', _ => 'L' };
        return new ParkingSlot($"L{level}-{code}{position:D2}", level, size);   // L1-S01, L1-M03, L2-L06
    }
}

public static class LotFactory
{
    public static IReadOnlyList<Level> CreateLevels(IEnumerable<LevelConfig> layout, ISlotFactory slotFactory)
    {
        var levels = new List<Level>();
        foreach (var cfg in layout)
        {
            var slots = new List<ParkingSlot>();
            int position = 1;                                          // numbered across the whole level
            foreach (var (size, count) in new[] { (SlotSize.Small, cfg.Small), (SlotSize.Medium, cfg.Medium), (SlotSize.Large, cfg.Large) })
                for (int i = 0; i < count; i++)
                    slots.Add(slotFactory.Create(cfg.Level, size, position++));
            levels.Add(new Level(cfg.Level, slots));
        }
        return levels;
    }
}
""", "ParkingLot.Core/PricingAndSetup.cs")}
{C(r"""
namespace ParkingLot.Core;

public sealed class CapacityEventArgs(VehicleType vehicleType, int freeSlots) : EventArgs
{
    public VehicleType VehicleType { get; } = vehicleType;
    public int FreeSlots { get; } = freeSlots;
}

public class ParkingLotService
{
    private readonly IReadOnlyList<Level> _levels;
    private readonly IClock _clock;
    private readonly Dictionary<string, ParkingSlot> _slotsById;
    private readonly Dictionary<string, Ticket> _openById = new(StringComparer.OrdinalIgnoreCase);
    private readonly Dictionary<string, Ticket> _openByVehicle = new(StringComparer.OrdinalIgnoreCase);
    private IPricingStrategy _pricing;
    private int _ticketSequence;

    // ---- Observer: displays and alerts subscribe; the lot doesn't know who listens ----
    public event EventHandler<CapacityEventArgs>? LotFull;           // no slot left for this vehicle type
    public event EventHandler<CapacityEventArgs>? SpaceAvailable;    // first slot freed after being full

    public string Name { get; }
    public IReadOnlyCollection<Ticket> OpenTickets => _openById.Values;

    public ParkingLotService(string name, IEnumerable<Level> levels, IPricingStrategy pricing, IClock clock)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(name);
        Name = name;
        _pricing = pricing ?? throw new ArgumentNullException(nameof(pricing));
        _clock = clock ?? throw new ArgumentNullException(nameof(clock));
        _levels = levels.OrderBy(l => l.Number).ToList();
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
        var ticket = new Ticket($"T{++_ticketSequence:D4}", vehicle, slot, _clock.Now);   // T0001, T0002…
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
        RaiseCapacityChanges(before);
        return Result<Ticket>.Ok(ticket);
    }

    public int FreeSlotsFor(VehicleType type) => _slotsById.Values.Count(s => s.IsFree && s.CanFit(type));

    public IReadOnlyList<LevelAvailability> Availability() =>
        _levels.Select(level => new LevelAvailability(level.Number,
                    Enum.GetValues<SlotSize>()
                        .Select(size => new SlotCount(size,
                            Free:  level.Slots.Count(s => s.Size == size && s.IsFree),
                            Total: level.Slots.Count(s => s.Size == size)))
                        .ToList()))
               .ToList();

    private Dictionary<VehicleType, int> FreeByType() =>
        Enum.GetValues<VehicleType>().ToDictionary(t => t, FreeSlotsFor);

    private void RaiseCapacityChanges(Dictionary<VehicleType, int> before)
    {
        foreach (var type in Enum.GetValues<VehicleType>())
        {
            int now = FreeSlotsFor(type);
            if (before[type] > 0 && now == 0) LotFull?.Invoke(this, new CapacityEventArgs(type, 0));
            else if (before[type] == 0 && now > 0) SpaceAvailable?.Invoke(this, new CapacityEventArgs(type, now));
        }
    }

    // Smallest fitting size, lowest level first. OrderBy is stable, so within a level slots keep the
    // factory's order. Never sort by the Id string: unpadded ids would put "M10" before "M2".
    private ParkingSlot? FindSlot(VehicleType type) =>
        _levels.SelectMany(l => l.Slots)
               .Where(s => s.IsFree && s.CanFit(type))
               .OrderBy(s => s.Size)
               .ThenBy(s => s.Level)
               .FirstOrDefault();
}
""", "ParkingLot.Core/ParkingLotService.cs")}
{C(r"""
using ParkingLot.Core;

// Composition root: every concrete choice lives here
var clock = new ManualClock(new DateTime(2026, 11, 12, 9, 0, 0));          // Thu 12 Nov 2026, 09:00 (local time)
var levels = LotFactory.CreateLevels(
    [new LevelConfig(1, Small: 2, Medium: 3, Large: 1), new LevelConfig(2, Small: 2, Medium: 3, Large: 1)],
    new StandardSlotFactory());
var rates = new Dictionary<VehicleType, decimal>
    { [VehicleType.Bike] = 10m, [VehicleType.Car] = 40m, [VehicleType.Truck] = 100m };
var lot = new ParkingLotService("City Centre Parking", levels, new HourlyPricing(rates), clock);

lot.LotFull += (_, e) => Console.WriteLine($"  DISPLAY: {e.VehicleType} parking full");
lot.SpaceAvailable += (_, e) => Console.WriteLine($"  DISPLAY: {e.VehicleType} parking open ({e.FreeSlots} free)");

var car = lot.Park(new Vehicle("KA01AB1234", VehicleType.Car));
Console.WriteLine(car.Success ? $"Ticket {car.Value!.Id} → {car.Value.SlotId}" : car.Error);
// Ticket T0001 → L1-M03

Console.WriteLine(lot.Park(new Vehicle("ka-01-ab-1234", VehicleType.Car)).Error);
// KA01AB1234 is already parked at L1-M03 (ticket T0001)

lot.Park(new Vehicle("MH12TR0001", VehicleType.Truck));                  // L1-L06
lot.Park(new Vehicle("MH12TR0002", VehicleType.Truck));                  // L2-L06, the last Large slot
//   DISPLAY: Truck parking full

clock.Advance(TimeSpan.FromMinutes(150));
var exit = lot.Exit("T0001").Value!;
Console.WriteLine($"{exit.Vehicle} paid ₹{exit.Amount:N2} after {exit.Duration(clock.Now)}");
// Car KA01AB1234 paid ₹120.00 after 02:30:00

foreach (var level in lot.Availability())
    Console.WriteLine($"L{level.Level}: " + string.Join("  ", level.Counts.Select(c => $"{c.Size} {c.Free}/{c.Total}")));
// L1: Small 2/2  Medium 3/3  Large 0/1
// L2: Small 2/2  Medium 3/3  Large 0/1
""", "ParkingLot.App/Program.cs (demo)")}
{C(r"""
using ParkingLot.Core;

namespace ParkingLot.Tests;

public class ParkingLotServiceTests
{
    private static readonly Dictionary<VehicleType, decimal> Rates = new()
        { [VehicleType.Bike] = 10m, [VehicleType.Car] = 40m, [VehicleType.Truck] = 100m };

    private readonly ManualClock _clock = new(new DateTime(2026, 11, 12, 9, 0, 0));   // no extra package needed

    private ParkingLotService CreateLot(int small = 1, int medium = 1, int large = 1) =>
        new("Test lot",
            LotFactory.CreateLevels([new LevelConfig(1, small, medium, large)], new StandardSlotFactory()),
            new HourlyPricing(Rates), _clock);

    [Fact]
    public void Exit_CarAfterTwoHoursThirty_Charges120()
    {
        var lot = CreateLot();
        var ticket = lot.Park(new Vehicle("MH12XY9999", VehicleType.Car)).Value!;

        _clock.Advance(TimeSpan.FromMinutes(150));
        var closed = lot.Exit(ticket.Id).Value!;

        Assert.Equal(120m, closed.Amount);                    // 3 started hours × ₹40
        Assert.Equal(TimeSpan.FromMinutes(150), closed.Duration(_clock.Now));
    }

    [Theory]
    [InlineData(10, 0)]       // inside the grace period
    [InlineData(11, 40)]      // first started hour
    [InlineData(60, 40)]
    [InlineData(61, 80)]      // second hour started
    public void Calculate_Car_UsesGraceAndStartedHours(int minutes, int expected)
    {
        var entry = new DateTime(2026, 11, 12, 9, 0, 0);
        var fee = new HourlyPricing(Rates).Calculate(VehicleType.Car, entry, entry.AddMinutes(minutes));
        Assert.Equal((decimal)expected, fee);
    }

    [Fact]
    public void Park_CarWhenMediumFull_UsesLargeSlot()
    {
        var lot = CreateLot(small: 0, medium: 1, large: 1);  // slots L1-M01, L1-L02
        lot.Park(new Vehicle("DL3CAA0001", VehicleType.Car));

        var second = lot.Park(new Vehicle("DL3CAA0002", VehicleType.Car));

        Assert.True(second.Success);
        Assert.Equal("L1-L02", second.Value!.SlotId);
    }

    [Fact]
    public void Park_FillsSlotsInFactoryOrder_NotStringOrder()
    {
        var lot = CreateLot(small: 0, medium: 12, large: 0);
        var ids = new List<string>();
        for (int i = 1; i <= 10; i++)
            ids.Add(lot.Park(new Vehicle($"KA01AB{i:D4}", VehicleType.Car)).Value!.SlotId);

        Assert.Equal("L1-M02", ids[1]);
        Assert.Equal("L1-M10", ids[9]);
    }

    [Fact]
    public void Park_TruckWhenNoLargeSlot_Fails()
    {
        var lot = CreateLot(small: 2, medium: 2, large: 0);

        var result = lot.Park(new Vehicle("TN09TR4321", VehicleType.Truck));

        Assert.False(result.Success);
        Assert.Empty(lot.OpenTickets);
    }

    [Fact]
    public void Park_LastLargeSlot_RaisesLotFullForTrucks()
    {
        var lot = CreateLot();
        var full = new List<VehicleType>();
        lot.LotFull += (_, e) => full.Add(e.VehicleType);

        lot.Park(new Vehicle("MH12TR0001", VehicleType.Truck));

        Assert.Equal(VehicleType.Truck, Assert.Single(full));   // only trucks are full; cars and bikes still fit
    }

    [Fact]
    public void Exit_SameTicketTwice_SecondFails()
    {
        var lot = CreateLot();
        var ticket = lot.Park(new Vehicle("KL07BK2468", VehicleType.Bike)).Value!;

        Assert.True(lot.Exit(ticket.Id).Success);
        Assert.False(lot.Exit(ticket.Id).Success);
    }
}
""", "ParkingLot.Tests/ParkingLotServiceTests.cs")}

<h3>6. Debrief: compare and write down</h3>
<ol>
<li>Which of the 10 design decisions did you make differently? Is yours worse, or just different? Write one sentence of justification for each difference.</li>
<li>Where did you lose the most time? (Usually: fee rounding, or deciding where allocation lives.)</li>
<li>What did you have to look up? Each lookup is a flashcard for Sunday.</li>
<li>Compare with your Week 9 version: what's better now? That's your Phase 1 progress, in one paragraph for your README.</li>
</ol>
{tip("In an interview LLD round you'd talk while designing: requirements → entities → relationships → key flows (enter, exit) → extensibility points. Practise narrating your decisions table out loud.")}
''',
["Starting to type code in minute one and redesigning at minute 60.",
"Using <code>double</code> for money or <code>Math.Round</code> where the rule says \"every started hour\" (that's <code>Math.Ceiling</code>).",
"Calling <code>DateTime.Now</code> inside the lot or pricing strategy, making fee tests impossible without waiting.",
"Building an inheritance tree (<code>Car : Vehicle</code>, <code>Bike : Vehicle</code>) that only differs by a value — an enum or data would do.",
"Peeking at the reference solution before the timer ends; the score becomes meaningless."],
("40 min, after the 2-hour build", ["Add a <code>WeekendPricing</code> strategy (flat ₹100 per day for cars entering on Saturday/Sunday) without changing <code>ParkingLotService</code>; prove it with a test using <code>ManualClock</code>.",
"Add an EV charging surcharge (₹15 per started hour on top of parking) and decide: an <code>EvChargingSlot</code> subclass (as in Week 9), a flag on the slot, or a decorator around the pricing strategy? Write down why.",
"Add an <code>EntranceDisplay</code> observer class (as in Week 9) that subscribes to <code>LotFull</code>/<code>SpaceAvailable</code>, and make sure the console code lives only in ParkingLot.App."]),
[("Why is SlotSize declared with explicit values 1, 2, 3?","So sizes are ordered and comparable: <code>Size &gt;= RequiredSize(type)</code> expresses \"big enough\" in one line."),
("Why does ParkingLotService.Park return Result&lt;Ticket&gt; instead of throwing when full?","A full lot is a normal, expected outcome the caller must handle, not a programming error. Exceptions are kept for bugs like passing null."),
("How do the tests control time?","The lot takes an IClock. Tests pass a ManualClock and call Advance(…) to move it instantly, so a 2.5-hour stay is tested in milliseconds — and no extra NuGet package is needed.")],
[("Basic","How would you start a parking lot design question in an interview?","Clarify requirements first: vehicle types, spot sizes, multiple levels/entrances, pricing rules, payment, whether to show availability. Then list the entities (ParkingLotService, Level, ParkingSlot, Vehicle, Ticket, IPricingStrategy), their relationships, and walk through the entry and exit flows before writing code."),
("Basic","Which design patterns fit a parking lot?","Strategy for fees (and optionally allocation), Factory for creating levels/spots, Singleton is often suggested for the lot but dependency injection with a single registered instance is the better modern answer. Observer can notify displays when availability changes."),
("Basic","How do you make the fee rule changeable without editing ParkingLotService?","Depend on an IPricingStrategy interface injected through the constructor (and swappable with ChangePricing). New rules (weekend, monthly pass, EV surcharge) are new classes; the service is closed for modification but open for extension (OCP, DIP)."),
("Intermediate","How would you find a free spot efficiently in a lot with 10,000 spots?","Keep free slots per size in separate structures, e.g. a SortedSet or PriorityQueue ordered by (level, distance) per SpotSize, removing on park and adding back on exit. Allocation becomes O(log n) instead of scanning every spot."),
("Intermediate","How would you handle two cars arriving at two gates at the same time?","Allocation must be atomic: a lock around Park in a single process, or in a distributed system a database transaction/row lock (or a conditional update like UPDATE … WHERE IsFree = 1) so two gates can't claim the same slot. Week 7's concurrency and Week 13's transactions cover the tools."),
("Intermediate","Why is Vehicle a record but ParkingSlot and Ticket classes?","A vehicle is an immutable value (normalised number + type), so a record's value equality fits. A slot and a ticket are entities: their identity matters and their state changes (occupancy; exit time and amount when the ticket is closed), so they're classes with controlled mutation through internal methods.")])

def model(t): return f'<div class="note tip"><b>Model 2-minute answer.</b> {t}</div>'

# ================= DAY 5 =================
d5 = day(5, "FRI", "Explain it aloud: value vs reference, GC, async/await and SOLID",
"Turn what you know into what you can <i>say</i>: give a clear two-minute spoken answer on the four topics every .NET interview probes, avoid the classic wrong answers, and survive the follow-ups.",
[("Value type","A type whose variables contain the data itself (struct, enum, int, decimal, DateTime). Assignment copies the data."),
("Reference type","A type whose variables contain a reference to an object on the managed heap (class, record, string, array, delegate). Assignment copies the reference."),
("Boxing","Wrapping a value type in a heap object so it can be treated as <code>object</code> or an interface."),
("Managed heap","Memory the CLR allocates objects from and the garbage collector reclaims."),
("GC roots","Starting points the GC traces from: static fields, local variables and parameters in active methods, CPU registers, GC handles."),
("Generations 0/1/2","The GC groups objects by age; most objects die young, so gen 0 is collected often and cheaply, gen 2 rarely."),
("Large Object Heap (LOH)","Where objects of 85,000 bytes or more go; collected with gen 2 and not compacted by default."),
("Finalizer","A <code>~ClassName()</code> method the GC calls before reclaiming an object; a last-resort safety net for unmanaged resources."),
("IDisposable","The pattern for releasing resources deterministically with <code>Dispose()</code>, usually via <code>using</code>."),
("async / await","Language support for writing asynchronous code sequentially; the compiler turns the method into a state machine."),
("Continuation","The rest of an async method after an <code>await</code>, scheduled to run when the awaited task completes."),
("SynchronizationContext","Decides where continuations run (UI thread in WPF/WinForms; ASP.NET Core has none)."),
("SOLID","Five design principles: Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion.")],
["Structure every answer: <b>define → how it works → example from your code → trade-off or gotcha</b>.",
"Two minutes is about 250–300 spoken words. Record yourself; most people ramble past four minutes.",
"Use your own projects as examples: Bank, Library, Parking Lot, Downloader. It proves experience.",
"Say \"it depends\" only if you immediately say <i>on what</i>.",
"If you don't know a follow-up, say what you'd check and how — never invent.",
"Repeat each topic until you can do it without \"um\" in the first 20 seconds."],
f'''
<h3>1. How to run today's session</h3>
{table(["Step","Time","What to do"],[
["Warm-up","10 min","Read the four model answers below once, aloud. Then close the page."],
["Round 1","4 × 5 min","Phone timer at 2:00 per topic. Record audio. Don't stop if you stumble."],
["Review","20 min","Listen back. Tick the 'key points' list for each topic. Note filler words and wrong statements."],
["Round 2","4 × 5 min","Re-record each topic, fixing what you missed. Then answer two follow-ups per topic."],
["Mock","25 min","Answer the six interview questions at the bottom as if live, then open them to compare."]])}
{table(["Part of the answer","Purpose","Value vs reference example"],[
["Define (1 sentence)","Show you know the term precisely","\"A value-type variable holds the data; a reference-type variable holds a reference to an object.\""],
["How it works","Show depth","Copy semantics, where memory lives, boxing"],
["Example from your code","Show experience","\"Transaction in my bank is a readonly record struct because…\""],
["Trade-off / gotcha","Show judgement","\"Large mutable structs get copied silently — keep structs small and readonly.\""]])}

<h3>2. Value vs reference types</h3>
{model("Value types — structs, enums, and primitives like int, decimal and DateTime — store their data directly in the variable, so assigning or passing one copies the data. Reference types — classes, records, strings, arrays, delegates — store a reference to an object on the managed heap, so assignment copies the reference and both variables point to the same object. A common misconception is that value types always live on the stack; they actually live wherever their container lives: a local int is on the stack or in a register, but an int field inside a class lives on the heap with that object. When a value type is converted to object or an interface it's boxed, which allocates a heap copy. In my bank simulator, Transaction is a readonly record struct — small, immutable, no heap allocation per ledger entry — while Account is a class because it has identity and changing state that must be shared. The gotcha: mutating a struct you got from a list indexer or a property only changes a copy. So I keep structs small and readonly, and use classes for anything with identity.")}
{C(r"""
var s1 = new PointS { X = 1 };
var s2 = s1;          // copies the data
s2.X = 99;
Console.WriteLine(s1.X);   // 1

var c1 = new PointC { X = 1 };
var c2 = c1;          // copies the reference — same object
c2.X = 99;
Console.WriteLine(c1.X);   // 99

void Reset(PointC p) { p.X = 0; p = new PointC(); p.X = 5; }   // reference passed BY VALUE
Reset(c1);
Console.WriteLine(c1.X);   // 0 — the mutation is visible, the reassignment is not

object boxed = s1;    // boxing: heap allocation of a copy
s1.X = 7;
Console.WriteLine(((PointS)boxed).X);   // 1 — the box holds the old copy

// Type declarations go after the top-level statements (otherwise CS8803)
public struct PointS { public int X; }
public class  PointC { public int X; }
""", "ValueVsReference.cs")}
{table(["Interviewer listens for","Common wrong answer","Why it's wrong"],[
["Copy semantics on assignment and parameter passing","\"Value types are on the stack, reference types on the heap\" (full stop)","Value-type fields of classes, array elements and boxed values live on the heap"],
["Boxing and its cost","\"Reference types are passed by reference\"","The reference is passed by value; only <code>ref</code>/<code>out</code>/<code>in</code> pass by reference"],
["string is a reference type that behaves like a value (immutable, == compares content)","\"string is a value type\"","It's a class; immutability and overloaded == make it feel like a value"],
["When to choose a struct (small, immutable, short-lived)","\"Structs are always faster\"","Large structs cost more to copy than a reference; mutable structs cause bugs"]])}
<p><b>Follow-ups to practise:</b> What does <code>ref</code> do with a reference type? (Lets the method replace the caller's reference.) Where does a lambda's captured local live? (In a compiler-generated closure class on the heap.) Can a struct be null? (Only as <code>Nullable&lt;T&gt;</code>.) What's a <code>ref struct</code>? (A stack-only type such as <code>Span&lt;T&gt;</code>; it can't be boxed or stored on the heap.)</p>

<h3>3. Garbage collection</h3>
{model("The .NET garbage collector automatically reclaims managed heap memory that's no longer reachable. It doesn't use reference counting; it traces. Starting from roots — static fields, locals and parameters of running methods, CPU registers — it marks every object it can reach; everything else is garbage. It then compacts the survivors to remove gaps, updating references. The heap is generational because most objects die young: new objects go into gen 0, which is collected often and quickly; survivors are promoted to gen 1 and then gen 2, which is collected rarely. Objects of 85,000 bytes or more go on the Large Object Heap, collected with gen 2 and not compacted by default, so large temporary arrays are expensive — that's why ArrayPool exists. The GC only manages memory: files, sockets and database connections must be released deterministically with IDisposable and using; finalizers are only a slow safety net. In my downloader I wrap the response and file streams in using, and share one HttpClient. Most 'memory leaks' in .NET are objects still reachable by accident — an event subscription on a long-lived publisher, or a static cache that never evicts.")}
{C(r"""
// 1. Deterministic cleanup: the GC does NOT close files or connections
using (var writer = new StreamWriter("statement.csv"))
{
    writer.WriteLine("Date,Description,Amount");
}                                   // Dispose() → flushed and closed here, not "some time later"

// 2. Seeing generations
var order = new object();
Console.WriteLine(GC.GetGeneration(order));   // 0
GC.Collect();                                  // demo only — don't call this in real code
Console.WriteLine(GC.GetGeneration(order));   // 1 (survived one collection; order is still used below)
GC.KeepAlive(order);

// 3. A classic managed leak: the long-lived publisher keeps the subscriber reachable
//    (type declarations must come after the top-level statements)
public class RateTicker                                 // lives for the whole app
{
    public event EventHandler<decimal>? RateChanged;
    public void Publish(decimal rate) => RateChanged?.Invoke(this, rate);
}
public class QuoteWindow : IDisposable
{
    private readonly RateTicker _ticker;
    public QuoteWindow(RateTicker ticker) { _ticker = ticker; _ticker.RateChanged += OnRate; }
    private void OnRate(object? sender, decimal rate) => Console.WriteLine($"USD/INR {rate}");
    public void Dispose() => _ticker.RateChanged -= OnRate;   // without this, every window ever opened stays alive
}
""", "GcDemo.cs")}
{table(["Interviewer listens for","Common wrong answer","Why it's wrong"],[
["Reachability from roots, mark and compact","\"It counts references\"","That's COM/Swift; .NET traces, so cycles are collected fine"],
["Generations and why (most objects die young)","\"Setting a variable to null frees memory\"","It only removes one root; memory is reclaimed at the next relevant collection (and the JIT already knows when a local is no longer used)"],
["IDisposable vs finalizer","\"The GC calls Dispose\"","It never does; finalizers run if defined, and Dispose is for <i>you</i> to call via using"],
["LOH, ArrayPool, avoiding allocations in hot paths","\"Call GC.Collect to fix memory problems\"","Forced collections promote objects and pause threads; find the root that keeps objects alive instead"]])}
<p><b>Follow-ups to practise:</b> Workstation vs server GC? (Server GC uses a heap and GC thread per core for throughput; ASP.NET Core uses it by default.) What is the dispose pattern with <code>Dispose(bool)</code>? (Only needed when a class directly owns unmanaged handles; otherwise a simple Dispose is enough, and SafeHandle is preferred.) How would you investigate a leak? (<code>dotnet-counters</code> to watch heap size, <code>dotnet-gcdump</code>/<code>dotnet-dump</code> to see what roots keep objects alive — Week 8.)</p>

<h3>4. async / await</h3>
{model("async and await let me write non-blocking code that reads like sequential code. Marking a method async lets me use await inside it; the compiler rewrites the method into a state machine. When execution hits an await on a task that hasn't finished, the method returns an incomplete Task to its caller and the thread is released to do other work. When the awaited operation completes, the rest of the method — the continuation — is resumed, on the captured SynchronizationContext if there is one (a UI thread), or on a thread-pool thread otherwise, as in ASP.NET Core. The key point is that for I/O like HTTP calls or database queries, no thread is blocked while waiting, which is why a web server can handle thousands of concurrent requests with a few threads. async doesn't create threads by itself; for CPU-bound work you'd use Task.Run, and only at the app level. Rules I follow: async all the way, never .Result or .Wait(), which block and can deadlock; no async void except event handlers; pass a CancellationToken; and use Task.WhenAll for independent operations. In my Week 7 downloader, WhenAll with a SemaphoreSlim downloaded files concurrently with a limit, and cancellation stopped them cleanly.")}
{C(r"""
public async Task<decimal> GetInvoiceTotalAsync(int invoiceId, CancellationToken ct)
{
    Console.WriteLine($"Before await: thread {Environment.CurrentManagedThreadId}");
    Invoice invoice = await _repository.GetAsync(invoiceId, ct);   // thread released while the DB works
    Console.WriteLine($"After await:  thread {Environment.CurrentManagedThreadId}");   // may differ (no sync context)
    return invoice.Lines.Sum(l => l.Amount);
}

// Sequential: ~3 s total          // Concurrent: ~1 s total
var a = await GetRateAsync("USD", ct);       var ta = GetRateAsync("USD", ct);
var b = await GetRateAsync("EUR", ct);       var tb = GetRateAsync("EUR", ct);
var c = await GetRateAsync("GBP", ct);       var tc = GetRateAsync("GBP", ct);
                                             decimal[] rates = await Task.WhenAll(ta, tb, tc);

// ❌ Blocking on async code
decimal total = GetInvoiceTotalAsync(42, ct).Result;   // ties up a thread; deadlocks under a UI/legacy ASP.NET context

// CPU-bound work: offload at the edge (UI / console), not inside library methods
var report = await Task.Run(() => BuildYearlyGstReport(transactions));
""", "AsyncDemo.cs (fragment: _repository, GetRateAsync and BuildYearlyGstReport are assumed)")}
{table(["Interviewer listens for","Common wrong answer","Why it's wrong"],[
["State machine, continuation, thread released at an incomplete await","\"async runs the method on a new thread\"","It runs synchronously until the first incomplete await; no new thread is created"],
["I/O vs CPU-bound distinction","\"await blocks until the task finishes\"","It suspends the <i>method</i>, not the thread"],
["Deadlock from .Result/.Wait() with a SynchronizationContext","\"ConfigureAwait(false) makes it faster everywhere\"","It only avoids resuming on the captured context; matters in libraries and UI apps, not in ASP.NET Core"],
["async void dangers, cancellation, WhenAll","\"Task.Run makes I/O async\"","It just moves blocking work to another thread; real async I/O needs async APIs"]])}
<p><b>Follow-ups to practise:</b> Task vs ValueTask? (ValueTask avoids an allocation when results are often synchronous; it must be awaited only once.) What happens to an exception in an awaited task? (It's rethrown at the await; with WhenAll the first is rethrown and all are in <code>task.Exception</code>.) How do you limit concurrency? (SemaphoreSlim with WaitAsync, or <code>Parallel.ForEachAsync</code> with MaxDegreeOfParallelism.)</p>

<h3>5. SOLID</h3>
{model("SOLID is five principles for code that's easy to change. Single Responsibility: a class should have one reason to change — in my grade analyzer, parsing CSV, grading rules and console output are separate classes. Open/Closed: add behaviour by adding code, not editing working code — the parking lot takes an IPricingStrategy, so a weekend rule is a new class. Liskov Substitution: a subtype must work anywhere its base type is expected without surprising the caller — my SavingsAccount and CurrentAccount both honour Withdraw's contract through AvailableToWithdraw instead of one of them throwing NotSupportedException. Interface Segregation: prefer small, focused interfaces so clients don't depend on methods they don't use — a read-only report needs IReadRepository, not a repository with Delete. Dependency Inversion: high-level policy depends on abstractions, not on concrete details — the lot depends on IClock and IPricingStrategy, which are injected, which is also what makes it testable. I treat SOLID as guidelines, not laws: applying every principle to a 50-line console tool is over-engineering; I introduce an abstraction when there's a second implementation or a testing need.")}
{C(r"""
// S — one reason to change each
public static class MarksCsvParser { /* text → records */ }
public static class GradeBands     { /* the grading rule */ }

// O + D — new pricing = new class; ParkingLot never changes
public interface IPricingStrategy { string Name { get; } decimal Calculate(VehicleType type, DateTime entry, DateTime exit); }
public sealed class FestivalFlatPricing(decimal perStartedHour) : IPricingStrategy   // Diwali week offer
{
    public string Name => "Festival flat";
    public decimal Calculate(VehicleType type, DateTime entry, DateTime exit) =>
        exit - entry <= TimeSpan.FromMinutes(10) ? 0m : (decimal)Math.Ceiling((exit - entry).TotalHours) * perStartedHour;
}

// L — violation: callers of Account.Withdraw can't trust it any more
public class FixedDeposit : Account
{
    public FixedDeposit(string holder) : base("FD", holder, 0m) { }
    public override string Kind => "FD";
    public override decimal AvailableToWithdraw => 0m;     // ✓ honours the contract (Withdraw throws InsufficientFunds)
    // ❌ public new void Withdraw(...) => throw new NotSupportedException();   // surprises every caller
}

// I — clients depend only on what they use
public interface IReadRepository<T>  { T? GetById(int id); IReadOnlyList<T> GetAll(); }
public interface IWriteRepository<T> { void Add(T entity); bool Remove(int id); }
""", "SolidExamples.cs (fragment: Account/Vehicle from earlier weeks)")}
{table(["Interviewer listens for","Common wrong answer","Why it's wrong"],[
["A concrete example per letter from <i>your</i> code","Reciting the five names with textbook definitions only","Shows memory, not experience"],
["LSP as behavioural (contracts), not just compiles","\"LSP means you can cast a child to a parent\"","The compiler guarantees that; LSP is about not breaking expectations (Square/Rectangle, NotSupportedException)"],
["DIP vs DI distinction","\"Dependency inversion = using a DI container\"","DIP is the design principle; DI (constructor injection) is a technique; a container is a tool"],
["Pragmatism","\"Every class needs an interface\"","Interfaces with one implementation and no test need are noise (YAGNI)"]])}
<p><b>Follow-ups to practise:</b> Give an example of an OCP violation in your code. (The pre-Week-9 fee <code>switch</code> inside the lot.) How does SOLID relate to testability? (DIP lets tests inject fakes; SRP keeps units small.) Which principle do you break most often, and why? (A good honest answer: SRP in Program.cs for small tools, deliberately.)</p>
''',
["Talking for five minutes: interviewers stop listening after two. Practise with a timer.",
"Opening with \"so basically…\" and a history lesson instead of a one-sentence definition.",
"Giving only textbook examples (Animal/Dog) instead of your own projects.",
"Stating a myth confidently (\"value types live on the stack\", \"async creates threads\").",
"Answering a follow-up you don't know by guessing, instead of reasoning aloud about how you'd find out."],
("40 min", ["Record all four topics at 2:00 each, transcribe one, and count filler words and inaccuracies.",
"For each topic write the three follow-up questions you'd least like to be asked, and draft a 30-second answer to each.",
"Explain async/await to a non-programmer friend using a restaurant analogy (waiter takes the next order while the kitchen cooks), then to yourself using the state machine. Note which version you understand better."]),
[("Where does an int field of a class instance live?","On the managed heap, inside the object that contains it. \"Value types live on the stack\" is only true for locals (and not always even then)."),
("What actually happens at an await on an incomplete task?","The method registers its continuation on the task, returns an incomplete Task to its caller, and the current thread is free. When the task completes, the continuation runs (on the captured context or the thread pool)."),
("Does the GC ever call Dispose?","No. Dispose is called by your code (usually via using). The GC may call a finalizer, which a well-written class uses only as a backup for unmanaged resources.")],
[("Basic","Explain value types vs reference types.","Value types (structs, enums, primitives) hold their data directly; assignment and parameter passing copy the data. Reference types (classes, records, strings, arrays) hold a reference to a heap object; assignment copies the reference, so both variables see the same object. Value types live inline wherever their container lives; converting one to object/interface boxes it on the heap."),
("Basic","How does the .NET garbage collector work?","It's a tracing, generational, compacting collector. From roots (statics, locals, registers) it marks reachable objects, reclaims the rest and compacts survivors. Gen 0 holds new objects and is collected often; survivors move to gen 1 and gen 2. Objects ≥ 85,000 bytes go to the LOH. It manages memory only; other resources need IDisposable."),
("Basic","What does async/await do?","It lets you write asynchronous code sequentially. The compiler generates a state machine; at an await on an incomplete task the method returns to its caller and the thread is released; when the task completes the continuation resumes. For I/O this means no threads are blocked while waiting, improving scalability."),
("Intermediate","Why can .Result or .Wait() deadlock?","In an environment with a single-threaded SynchronizationContext (UI apps, classic ASP.NET), the blocked thread is the one the awaited continuation needs to resume on. The continuation waits for the thread, the thread waits for the task: deadlock. Fix: await all the way up; ConfigureAwait(false) in library code reduces the risk."),
("Intermediate","Explain the Liskov Substitution Principle with a real example.","Subtypes must be usable through the base type without breaking callers' expectations. If FixedDeposit inherited Account but threw NotSupportedException from Withdraw, code that withdraws from any Account would break. Instead, FixedDeposit reports AvailableToWithdraw = 0 so the normal InsufficientFunds rule applies — same contract, different data."),
("Intermediate","What's the difference between Dependency Inversion and Dependency Injection?","Dependency Inversion is the principle: high-level modules depend on abstractions, and details implement them. Dependency Injection is a technique to supply those implementations from outside, usually via the constructor. A DI container (Microsoft.Extensions.DependencyInjection) is just a tool that automates the wiring.")])

# ================= DAY 6 =================
d6 = day(6, "SAT", "Portfolio day: polish READMEs, add CI and pin your best repos",
"Make your Phase 1 work visible and credible: every repo gets a proper README and a green GitHub Actions build, your profile gets a README, and 4–6 repos are pinned with CV-ready descriptions. Budget: about 4 hours.",
[("GitHub Actions","GitHub's built-in CI/CD: YAML workflows in <code>.github/workflows/</code> run on events like push and pull_request."),
("Workflow / job / step","A workflow contains jobs; each job runs on a fresh runner VM and executes steps (actions or shell commands)."),
("Runner","The machine a job runs on, e.g. <code>ubuntu-latest</code>, <code>windows-latest</code>."),
("Status badge","An SVG image in the README showing whether the latest workflow run passed."),
("Branch protection","Repository rules such as \"require a pull request and a passing status check before merging to main\"."),
("Profile README","A README in a repo named exactly like your username; GitHub shows it at the top of your profile.")],
["A recruiter spends under a minute per repo: badges, one-line pitch, screenshot, how to run.",
"CI on every repo proves the code builds and the tests pass on a clean machine, not just yours.",
"Pin quality over quantity: 4–6 repos you can talk about for ten minutes each.",
"CV bullets: action verb + what you built + technique + measurable result.",
"Tag a <code>v1.0.0</code> release on each finished project (Monday's skills)."],
f'''
<h3>Requirements for today</h3>
<ul>
<li>Every Phase 1 repo has: README from the template below, <code>.gitignore</code>, <code>.gitattributes</code>, a licence, and a green CI badge.</li>
<li>Repos with tests (Bank, Parking Lot, and any you added this week) run them in CI on push and pull requests.</li>
<li>At least one GIF or screenshot per console app.</li>
<li>A profile README introducing you and linking the pinned projects.</li>
<li>4–6 pinned repos; repo descriptions and topics filled in.</li>
<li>CV/LinkedIn bullets drafted for each project.</li>
</ul>

<h3>Scaffold (per repo)</h3>
{C(r"""
cd ~/src/bank-simulator
git switch -c docs/portfolio-polish
dotnet new gitignore --force             # refresh to the official .NET template
mkdir -p .github/workflows docs
# add: README.md, .gitattributes (Monday), LICENSE, .github/workflows/dotnet.yml, docs/demo.gif
gh repo edit --description "Console bank simulator in C# 12: accounts, ledger, events, domain exceptions, xUnit tests" \
             --add-topic csharp --add-topic dotnet --add-topic xunit --add-topic portfolio
""", lang="bash")}
{C(r"""
bank-simulator/
├─ .github/
│  └─ workflows/
│     └─ dotnet.yml
├─ docs/
│  └─ demo.gif
├─ Bank.Core/
├─ Bank.App/
├─ Bank.Tests/
├─ .editorconfig
├─ .gitattributes
├─ .gitignore
├─ Directory.Build.props
├─ global.json
├─ LICENSE
├─ README.md
└─ Bank.sln
""", lang="text")}

<h3>Step 1 — The CI workflow</h3>
{C(r"""
name: .NET CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:            # adds a "Run workflow" button in the Actions tab

permissions:
  contents: read

concurrency:                    # a new push cancels the still-running build for the same branch
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Restore
        run: dotnet restore

      - name: Check formatting
        run: dotnet format --verify-no-changes --no-restore

      - name: Build
        run: dotnet build --no-restore --configuration Release

      - name: Test
        run: >
          dotnet test --no-build --configuration Release
          --logger "trx;LogFileName=test-results.trx"
          --results-directory TestResults
          --collect:"XPlat Code Coverage"

      - name: Upload test results
        if: always()            # upload even when tests fail, so you can inspect them
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: TestResults
""", ".github/workflows/dotnet.yml", lang="yaml")}
{C(r"""
{
  "sdk": {
    "version": "8.0.400",
    "rollForward": "latestFeature"
  }
}
""", "global.json (pins the SDK band for everyone, including CI)", lang="json")}
{warn("If your global.json pins an SDK, the <code>dotnet-version</code> in the workflow must be able to satisfy it, or use <code>global-json-file: global.json</code> in setup-dotnet instead of <code>dotnet-version</code>.", "Watch out")}
{C(r"""
git add .github/workflows/dotnet.yml global.json
git commit -m "ci: build, format-check and test on push and PR"
git push -u origin docs/portfolio-polish
gh pr create --fill
gh run watch                       # follow the run live in the terminal
gh run list --limit 3
# STATUS  TITLE                                          WORKFLOW  BRANCH                 EVENT         ID
# ✓       ci: build, format-check and test on push...   .NET CI   docs/portfolio-polish  pull_request  11843...
""", lang="bash")}
<p>Then protect main: <b>Settings → Branches → Add rule</b> (or Rulesets) for <code>main</code>: require a pull request, require status check <code>build-and-test</code> to pass. From now on, broken code can't reach main.</p>

<h3>Step 2 — README template</h3>
{C(r"""
# Bank Simulator

[![.NET CI](https://github.com/<your-user>/bank-simulator/actions/workflows/dotnet.yml/badge.svg)](https://github.com/<your-user>/bank-simulator/actions/workflows/dotnet.yml)
![.NET 8](https://img.shields.io/badge/.NET-8.0-512BD4)
![C# 12](https://img.shields.io/badge/C%23-12-239120)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A console bank simulator with savings and current accounts, an immutable ledger,
low-balance and large-transaction alerts, and a domain exception hierarchy — covered by xUnit tests.

![Demo](docs/demo.gif)

## Features
- Savings (₹1,000 minimum balance, 3.5% p.a. monthly interest) and current (overdraft) accounts
- Transfers that never leave money half-moved
- Events for low balance and transactions ≥ ₹50,000
- Daily withdrawal limit and frozen accounts with clear error messages
- 25+ unit tests (facts, theories, exception and event tests)

## Tech
C# 12 · .NET 8 · records and record structs · pattern matching · events · xUnit · GitHub Actions

## Architecture
```mermaid
flowchart LR
    App[Bank.App<br/>console UI] --> Core[Bank.Core<br/>accounts, rules, events]
    Tests[Bank.Tests<br/>xUnit] --> Core
```
- **Bank.Core** has no Console or file access, so every rule is unit-testable.
- `Account` is abstract; `SavingsAccount` and `CurrentAccount` decide `AvailableToWithdraw`.
- `BankService` forwards every account's events so the UI subscribes once.

## Getting started
```bash
git clone https://github.com/<your-user>/bank-simulator.git
cd bank-simulator
dotnet run --project Bank.App
dotnet test
```

## Project structure
| Project | Purpose |
|---|---|
| `Bank.Core` | Domain model, rules, exceptions |
| `Bank.App` | Console menu |
| `Bank.Tests` | xUnit tests |

## What I learned
- Modelling immutable facts with `readonly record struct`
- Designing an exception hierarchy vs returning results
- Testing events with `Assert.Raises`

## Roadmap
- [ ] Persist accounts to JSON (Week 6 skills)
- [ ] Expose as a Web API (Phase 2)

## Licence
MIT
""", "README.md", lang="markdown")}
<h4>Screenshots and GIFs</h4>
{table(["Tool","Platform","Use"],[
["ScreenToGif","Windows","Record a terminal/window region, trim frames, export GIF"],
["Kap","macOS","Quick screen region recording to GIF/MP4"],
["Peek","Linux","Simple GIF screen recorder"],
["vhs (charmbracelet)","Any","Scripted terminal recordings from a <code>.tape</code> file — perfectly repeatable"],
["asciinema","macOS/Linux","Records terminal sessions as text; link or convert to GIF"]])}
<ul>
<li>Keep GIFs under ~10 seconds and ~5 MB; show one complete flow (open account → withdraw → alert).</li>
<li>Use a large terminal font (16–18 pt) and a clean prompt; hide your username/path if you like.</li>
<li>Store media in <code>docs/</code> and reference with a relative path so it works in forks.</li>
<li>For APIs and web apps later (Phase 2–3), screenshots of Swagger UI and the UI replace GIFs.</li>
</ul>

<h3>Step 3 — Profile README</h3>
{C(r"""
gh repo create <your-user> --public --add-readme --description "My GitHub profile"
# the repo name must match your username exactly; GitHub then shows its README on your profile
""", lang="bash")}
{C(r"""
### Hi, I'm Samrath

.NET developer building AI-powered tooling, currently on a 74-week full-stack .NET roadmap
(C# → SQL Server & EF Core → ASP.NET Core APIs → frontend → Azure → microservices).

**Now:** Phase 1 complete — C#, OOP, LINQ, async, design patterns, Git, unit testing.
**Next:** SQL Server, EF Core and Web APIs.

#### Featured projects
| Project | What it shows |
|---|---|
| [Parking Lot](https://github.com/<your-user>/parking-lot) | Low-level design, Strategy/Factory/Observer, injected clock, xUnit |
| [Bank Simulator](https://github.com/<your-user>/bank-simulator) | Records, events, exception hierarchy, 25+ tests |
| [Async Downloader](https://github.com/<your-user>/async-downloader) | async/await, cancellation, progress, throttled concurrency |
| [Expense Tracker](https://github.com/<your-user>/expense-tracker) | File I/O, JSON/CSV serialization, LINQ reports |

**Tech:** C# · .NET 8 · xUnit · Git · GitHub Actions — learning: SQL Server · EF Core · ASP.NET Core

[LinkedIn](https://www.linkedin.com/in/<your-handle>)
""", "<your-user>/README.md", lang="markdown")}

<h3>Step 4 — Choose what to pin</h3>
{table(["Repo","Pin?","Why"],[
["Parking Lot (W9, rebuilt W10)","Yes — first","Classic LLD interview topic; patterns, tests, clean design"],
["Bank Simulator (W3)","Yes","Domain modelling, events, exceptions, now with tests"],
["Async Downloader (W7)","Yes","async/await, cancellation and concurrency are senior-signal topics"],
["Expense Tracker (W6)","Yes","Real-world I/O, serialization, LINQ reporting"],
["City Library (W2/W4)","Optional","Good OOP + generic repository story; pin if its README is strong"],
["Grade Analyzer (W5)","Optional","LINQ showcase; merge into a \"csharp-exercises\" repo if small"],
["Toolkit / calculator (W1)","No","Too basic to pin; keep public as history"],
["dotnet-notes","Optional","Shows learning discipline; pin only if well organised"]])}
{tip("Pinned repos display the description and primary language, so fill in the description and topics with <code>gh repo edit</code>. Archive or make private any half-finished experiments that dilute the profile.")}

<h3>Step 5 — CV and LinkedIn bullets</h3>
<p>Formula: <b>Built/Designed/Implemented</b> + what + how (technique) + result (number or quality).</p>
{table(["Project","Bullet"],[
["Toolkit (W1)","Built a menu-driven C# console toolkit (calculator, unit and currency converters) with robust input validation using TryParse and switch expressions."],
["City Library (W2/W4)","Designed an object-oriented library management system in C# with an abstract item hierarchy and a generic <code>IRepository&lt;T&gt;</code>, replacing list scans with Dictionary/HashSet indexes for O(1) lookups and adding FIFO reservations."],
["Bank Simulator (W3)","Implemented a bank account simulator with an immutable ledger (record structs), event-driven low-balance and large-transaction alerts, and a domain exception hierarchy; covered rules with 25+ xUnit tests running in GitHub Actions."],
["Grade Analyzer (W5)","Built a LINQ-based student grade analyser that parses CSV marks, computes per-subject statistics and grade bands, and ranks students with GroupBy/OrderBy queries."],
["Expense Tracker (W6)","Developed a personal expense tracker with JSON persistence, CSV import/export and GST-aware monthly reports, using System.Text.Json and streaming file I/O."],
["Async Downloader (W7)","Built a concurrent file downloader using async/await, HttpClient streaming, SemaphoreSlim throttling, progress reporting and cooperative cancellation."],
["Parking Lot (W9/W10)","Designed a multi-level parking lot system applying SOLID and the Strategy pattern for pluggable pricing, with time-controlled unit tests via an injected clock; rebuilt from scratch in 2 hours as a design exercise."]])}
<p>For LinkedIn, add a <b>Projects</b> entry for each pinned repo with the same bullet and the GitHub link, and one post when Phase 1 is done: what you built, one thing you learned, link to the profile.</p>

<h3>Run it — what \"done\" looks like</h3>
{C(r"""
gh pr merge --squash --delete-branch
git switch main && git pull
git tag -a v1.0.0 -m "Bank Simulator 1.0" && git push origin v1.0.0
gh release create v1.0.0 --generate-notes
gh repo view --web          # badge green, GIF plays, description and topics visible
""", lang="bash")}

<h3>Stretch goals</h3>
<ul>
<li>Run the workflow on a matrix of <code>ubuntu-latest</code> and <code>windows-latest</code> (line-ending bugs show up fast).</li>
<li>Publish a self-contained single-file build as a release asset: <code>dotnet publish Bank.App -c Release -r win-x64 --self-contained -p:PublishSingleFile=true</code>, attached with <code>gh release upload</code>.</li>
<li>Add Dependabot (<code>.github/dependabot.yml</code>) for NuGet and GitHub Actions updates.</li>
<li>Combine Toolkit and Grade Analyzer into one <code>csharp-fundamentals</code> repo with a top-level README linking each.</li>
</ul>
''',
iqs=[("Basic","What does your CI pipeline do?","On every push to main and every pull request, GitHub Actions checks out the code on a clean Ubuntu runner, installs the .NET 8 SDK, restores packages, verifies formatting with dotnet format, builds in Release, runs the xUnit tests with coverage and uploads the results. Branch protection blocks merging unless it passes."),
("Basic","What makes a good README for a portfolio project?","A one-line pitch, status badges, a screenshot or GIF, a feature list, the tech used, a short architecture section, exact commands to run and test it, and what you learned. A reviewer should understand and run it within two minutes."),
("Intermediate","Why run dotnet format --verify-no-changes and tests in CI if you run them locally?","CI is the single, clean, reproducible source of truth: it catches \"works on my machine\" problems (uncommitted files, SDK differences, line endings), applies to every contributor, and combined with branch protection guarantees main always builds and passes."),
("Intermediate","Why use --no-restore and --no-build in later workflow steps?","Each step would otherwise repeat the previous work. Restoring once and building once makes the pipeline faster and ensures tests run against exactly the binaries the build step produced.")])

# ================= DAY 7 =================
d7 = day(7, "SUN", "Rest and buffer day: Phase 1 recap, self-assessment and Phase 2 setup",
"Take it light: look back at what Phase 1 gave you, mark your strengths and gaps honestly, and get your machine ready for SQL Server so Week 11 starts with learning, not installing.",
[("Buffer day","A planned slack day for catching up, revising weak spots or resting, so one bad week doesn't derail the whole roadmap."),
("Self-assessment","Rating each topic green (can explain and use), amber (can use with notes) or red (can't yet)."),
("Phase exit check","The end-of-phase review: rebuild something from scratch, explain the core topics aloud, polish the portfolio."),
("SQL Server Developer edition","The free, full-featured edition of SQL Server licensed for development and testing (not production).")],
["No new concepts today. Rest is part of the plan.",
"Spend at most 2 hours: 30 min self-assessment, 20 min quiz, 60 min setup, the rest is yours.",
"Reds go on next Saturday's list or a buffer day; don't try to fix them all today.",
"Do the Phase 2 installs now; Docker images and SSMS take a while to download."],
f'''
<h3>1. Phase 1 recap: what you can now do</h3>
<ul>
<li>Set up .NET projects and solutions from the CLI, and explain SDK, runtime, CLR, IL and JIT.</li>
<li>Model a domain with classes, records, structs, enums, interfaces and abstract classes, and choose between them.</li>
<li>Use pattern matching, exceptions (including your own hierarchy), delegates and events.</li>
<li>Pick the right collection for the access pattern and write generic types with constraints.</li>
<li>Query data with LINQ and understand deferred execution.</li>
<li>Read and write files, JSON and CSV safely with streams and <code>using</code>.</li>
<li>Write correct async code with cancellation and bounded concurrency.</li>
<li>Explain memory, the GC and value vs reference semantics.</li>
<li>Apply SOLID and common design patterns, and design a parking lot under time pressure.</li>
<li>Work with Git like a team member, write xUnit tests, and ship repos with READMEs and CI.</li>
</ul>
{table(["Week","Project","Status"],[
["1","Toolkit (calculator, converters)","Done"],
["2, 4","City Library (OOP, generic repository)","Done"],
["3, 10","Bank Simulator (+ tests and CI this week)","Done"],
["5","Grade Analyzer (LINQ)","Done"],
["6","Expense Tracker (files, JSON/CSV)","Done"],
["7","Async Downloader","Done"],
["9, 10","Parking Lot (rebuilt from scratch on Thursday)","Done"]])}

<h3>2. Self-assessment: mark each row G / A / R</h3>
<p class="muted">G = I can explain it aloud and use it without notes. A = I can use it with notes. R = I can't yet. Copy this into your <code>dotnet-notes</code> repo and fill in the last column.</p>
{table(["Week","Topic","Test yourself","G / A / R"],[
["1","C# basics","Explain value vs reference with an example; parse input safely with TryParse",""],
["2","OOP","Interface vs abstract class; virtual/override vs new; constructor chaining",""],
["3","Modern C# and exceptions","Records and <code>with</code>; property/list patterns; throw vs throw ex; events",""],
["4","Collections and generics","Big-O of List/Dictionary/HashSet; constraints; yield; IComparer vs IEqualityComparer",""],
["5","Delegates, lambdas, LINQ","Closures; GroupBy/Join/SelectMany; IEnumerable vs IQueryable",""],
["6","File I/O and serialization","Streams and using; System.Text.Json options; CSV edge cases",""],
["7","Async and concurrency","State machine; WhenAll; cancellation; SemaphoreSlim; why not .Result",""],
["8",".NET internals","GC generations and LOH; IDisposable; JIT/tiered compilation; Span&lt;T&gt;",""],
["9","SOLID and design patterns","One example per SOLID letter; Strategy, Factory, Observer, Decorator",""],
["10","Git, testing, review","Merge vs rebase; resolve a conflict; Fact vs Theory; Assert.Throws; CI workflow",""]])}

<h3>3. Mixed quiz (5 questions)</h3>
<details><summary>Q1. What prints?</summary>
{C(r"""
static async Task<int> WorkAsync()
{
    Console.Write("B");
    await Task.Delay(10);
    Console.Write("D");
    return 1;
}

Console.Write("A");
Task<int> t = WorkAsync();
Console.Write("C");
await t;
Console.Write("E");
""")}<b>ABCDE.</b> An async method runs synchronously until its first incomplete await, so B prints before control returns to the caller; D prints when the delay completes.</details>
<details><summary>Q2. What prints?</summary>
{C(r"""
var amounts = new List<int> { 100, 250, 400 };
var large = amounts.Where(a => a > 200);
amounts.Add(900);
Console.WriteLine(large.Count());
""")}<b>3.</b> Where is deferred: the filter runs when Count() enumerates, after 900 was added (250, 400, 900).</details>
<details><summary>Q3. What prints?</summary>
{C(r"""
var a = new Order(1, ["Pen"]);
var b = a with { Id = 2 };
b.Items.Add("Ink");
Console.WriteLine($"{a.Items.Count} {a == b}");

record Order(int Id, List<string> Items);
""")}<b>2 False.</b> <code>with</code> makes a shallow copy, so both records share the same list. They're not equal because the Ids differ.</details>
<details><summary>Q4. Does this test pass?</summary>
{C(r"""
[Fact]
public void Deposit_Negative_Throws()
{
    var account = new SavingsAccount("Asha Rao");
    Assert.Throws<ArgumentException>(() => account.Deposit(-100m));
}
""")}<b>No.</b> The code throws <code>ArgumentOutOfRangeException</code>. <code>Assert.Throws&lt;T&gt;</code> needs the exact type; use <code>Assert.Throws&lt;ArgumentOutOfRangeException&gt;</code> or <code>Assert.ThrowsAny&lt;ArgumentException&gt;</code>.</details>
<details><summary>Q5. How many new commits does main get?</summary>
{C(r"""
git switch -c feat/receipt      # branch from main
git commit -am "feat: receipt"  # one commit on the branch
git commit -am "test: receipt"  # two commits on the branch
git switch main                 # nobody has committed to main meanwhile
git merge feat/receipt
""", lang="bash")}<b>Two, and no merge commit.</b> main hasn't moved, so Git fast-forwards: main now points at the branch's second commit. With <code>--no-ff</code> there would also be a merge commit; with GitHub's squash merge, one new commit instead.</details>

<h3>4. How to use buffer days</h3>
{table(["If your week was…","Use the buffer day to…"],[
["Behind schedule","Finish the project's must-have requirements only; push stretch goals to the backlog"],
["On schedule, some reds","Re-study one red topic: re-read, retype one example, explain it aloud, add a test"],
["On schedule, all green/amber","Rest, or do one LeetCode-easy problem in C# and one mock interview question"],
["Tired or ill","Rest. A missed buffer day costs nothing; burnout costs weeks"]])}
<ul>
<li>One buffer day roughly every two weeks keeps a 74-week plan realistic.</li>
<li>Never use a buffer day to start the next week early; you'll lose the safety margin.</li>
<li>Write the reason in your notes repo (\"W10 buffer: redid async reds\"); patterns show you where the plan is too tight.</li>
</ul>

<h3>5. Phase 2 preview: SQL Server, EF Core and Web API (Weeks 11–22)</h3>
{table(["Week","Topic","You'll build"],[
["11","SQL Server foundations","Schema for a bank/library database, SELECT, JOINs, constraints"],
["12","Advanced T-SQL","Window functions, CTEs, pivoting, reporting queries"],
["13","Programmability and transactions","Stored procedures, functions, triggers, isolation levels"],
["14","Indexing and performance","Clustered/non-clustered indexes, execution plans"],
["15","ADO.NET, Dapper, EF Core basics","The same queries three ways from C#"],
["16","EF Core in depth","Migrations, relationships, tracking, performance"],
["17","ASP.NET Core fundamentals","Middleware, DI, configuration, minimal APIs vs controllers"],
["18","REST API design","Resources, status codes, paging, versioning, OpenAPI"],
["19","Cross-cutting concerns","Validation, logging, error handling, caching"],
["20","Authentication and authorization","JWT, policies, ASP.NET Core Identity"],
["21","Background jobs and real-time","Hosted services, queues, SignalR"],
["22","Phase 2 exit check","Rebuild and polish an API, mock interview"]])}
<h4>Set up before Monday</h4>
{C(r"""
# Option A (any OS): SQL Server in Docker
docker pull mcr.microsoft.com/mssql/server:2022-latest
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=Dev#Passw0rd2026" \
  -p 1433:1433 --name sql2022 -v sqldata:/var/opt/mssql \
  -d mcr.microsoft.com/mssql/server:2022-latest

docker logs sql2022 2>&1 | grep "ready for client connections"
docker exec -it sql2022 /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P 'Dev#Passw0rd2026' -C -Q "SELECT @@VERSION"
# Microsoft SQL Server 2022 (RTM-CU…) … Developer Edition (64-bit) on Linux …

docker stop sql2022 && docker start sql2022     # data survives in the 'sqldata' volume

# Option B (Windows): install SQL Server Developer edition from Microsoft's SQL Server downloads page
#                     (choose "Basic" install), then SSMS.

# Tools for both
dotnet tool install --global dotnet-ef           # EF Core CLI for Week 15–16 migrations
dotnet ef --version
""", lang="bash")}
{table(["Tool","Platform","Notes"],[
["SQL Server Management Studio (SSMS)","Windows","The full-featured client: execution plans, Profiler, backups. Install the latest version."],
["VS Code + MSSQL extension","Windows, macOS, Linux","Lightweight query editor and object explorer; the cross-platform choice."],
["Azure Data Studio","—","Microsoft announced its retirement (support ending February 2026); the recommended replacement is the MSSQL extension for VS Code."],
["Docker Desktop","Windows, macOS","On Apple Silicon, enable Rosetta (x86/amd64 emulation) — the SQL Server image is amd64-only."]])}
{C(r"""
Server=localhost,1433;Database=BankDb;User Id=sa;Password=Dev#Passw0rd2026;TrustServerCertificate=True;
""", "Connection string you'll use in Week 15 (dev only — secrets move to user-secrets in Week 17)", lang="text")}
{tip("Also download the AdventureWorks sample database backup (from Microsoft's sql-server-samples releases on GitHub). Week 11 restores it so you have realistic data to query from day one.")}

<h3>6. Close Phase 1</h3>
{C(r"""
cd ~/src/dotnet-notes
git add . && git commit -m "docs: Phase 1 self-assessment"
git tag -a phase-1-complete -m "Phase 1: C# and .NET fundamentals done"
git push && git push origin phase-1-complete
""", lang="bash")}

<div class="note tip"><b>Next week:</b> Week 11 — SQL Server foundations: databases, tables and data types, primary and foreign keys, constraints, SELECT with WHERE/ORDER BY, JOINs and GROUP BY, using the AdventureWorks sample and a schema for your bank simulator. Have SQL Server running and a client connected before Monday.</div>
''',
iqs=[("Basic","Walk me through one project from your portfolio.","Pick one (e.g. the parking lot): the problem in one sentence, the key design decisions (enums for sizes, Strategy for fees, injected IClock, Result for expected failures), one thing that was hard and how you solved it, how it's tested, and what you'd do next. Keep it to two minutes and invite questions."),
("Basic","How is a .NET solution with Core, App and Tests projects organised, and why?","The class library holds domain logic with no UI or I/O; the console (later web) app references it and handles input/output; the test project references only the library. This keeps rules testable, lets you swap the UI (console → Web API in Phase 2) and enforces dependencies pointing inward."),
("Intermediate","Looking back at your first projects, what would you change?","A good answer is specific: e.g. the Week 1 toolkit mixed console I/O with calculations, used double for money and had no tests; today I'd separate a core library, use decimal, inject a clock, add xUnit tests and CI. It shows growth and judgement."),
("Intermediate","What's the difference between ADO.NET, Dapper and EF Core?","ADO.NET is the low-level API: connections, commands and data readers, with manual mapping. Dapper is a micro-ORM over ADO.NET that maps query results to objects quickly while you write the SQL. EF Core is a full ORM: LINQ queries translated to SQL, change tracking, migrations and relationships. You'll use all three in Week 15 and learn when each fits.")])

days = "\n".join([d1,d2,d3,d4,d5,d6,d7])
cards = [
 (1,"MON","Git: branching, merge vs rebase, PRs, releases","Git workflow","Branches, fast-forward vs merge commit, rebase -i, conflicts, PRs, conventional commits, tags.","2 hrs"),
 (2,"TUE","Unit testing preview with xUnit","xUnit preview","Bank.Tests: Fact, Theory, InlineData, AAA, Assert.Throws, testing events, dotnet test.","2 hrs"),
 (3,"WED","Code review of your Phase 1 repos","Code review","Review checklist, before/after smells, .editorconfig, TreatWarningsAsErrors, dotnet format.","2 hrs"),
 (4,"THU","Timed rebuild: parking lot from scratch","Parking lot rebuild","2-hour time-boxed LLD, design decisions, self-scoring rubric, reference solution.","2 hrs"),
 (5,"FRI","Explain aloud: memory, GC, async, SOLID","Explain it aloud","Model 2-minute answers, what interviewers listen for, wrong answers, follow-ups.","2 hrs"),
 (6,"SAT","Portfolio: READMEs, CI and pinned repos","Portfolio &amp; CI","README template, GitHub Actions workflow, profile README, pins, CV bullets.","4 hrs"),
 (7,"SUN","Buffer day: recap and Phase 2 setup","Recap &amp; setup","Self-assessment, mixed quiz, buffer-day tips, SQL Server and tools installed.","4 hrs"),
]
build("/home/claude/build/week04.html", "/home/claude/build/week10.html", 10,
      "Week 10 — Git and Phase 1 exit check", "Phase 1", "~18 hrs",
      ["Phase 1 · Week 10 of 74",".NET 8 LTS / 9","C# 12","~18 hrs","Phase 1 exit"],
      "The last week of Phase 1 is about working like a professional and proving what you've learned. You'll master the Git workflow teams use, add your first xUnit tests to the bank simulator, review and refactor your own repos, rebuild the parking lot from scratch against the clock, explain the core topics aloud, and turn your projects into a portfolio with CI. Sunday is a light recap and Phase 2 setup.",
      cards, days)
print("built")
