# PicWise — the daily work

The owner, 2026-11-07: «Εφόσον ξέρεις το στόχο και το mission με ποιο τρόπο μπορούν να σε
εξουσιοδοτήσω έτσι ώστε να τρέχεις εσύ το project μέχρι την υλοποίηση του ... εσύ να βλέπεις
να διορθώνεις να ανεβάζεις ... και να με ρωτάς μόνο για τα σημαντικά με μία αποστολή email
την οποία εγώ θα εξετάζω ... μία φορά την ημέρα να εγκρίνω είναι απορρίπτω και εσύ να
αναλαμβάνεις το έργο για όλη την υπόλοιπη ημέρα». Told the gains and the risks, the owner
chose the hour: «12.00 μεσημέρι ώρα ελλάδος». The daily limit for the AI in measures, $2
(proposed, not objected to; the owner may change it).

Every day at about 12:00 Greek time a scheduled task starts a new session of Claude Code
on this repository. That session follows this file. Its last message is sent to the owner
by email and to their phone. The owner answers in that session, once a day.

## How a day goes

1. **Start.** Fetch `ccr-4f47068a-99ikwe` and work from it (fast-forward the session's
   own branch to it). Read, in this order: `PROJECT_RULES.md`, `docs/MISSION.md`, this
   file, the first section of `docs/picwise_session_handoff.md`, the last entries of
   `PROGRESS.md`. Read the session's notifications.
2. **Look.** What the last day left: an answer of the owner's in the last session (a
   «ναι» not yet acted on), a run to read, a deployment to check (the server's logs come
   only through the read-only workflows). On the cloud environment «picwise.concept»
   (owner, 2026-11-08: «στείλε το»; it allows only `picwise.subby.cloud`) a session may
   read the site's pages as a visitor sees them, with `curl`, which runs no script, so no
   search of the session's is kept among the visitors' searches (`/searched`); never a
   shop's link (an Awin tracked link), never a form.
   **Whether the night's preparation worked** (the audit's fixes, 2026-11-11,
   `docs/PICWISE_AUDIT_FIXES.md` 4.A.3): read `https://picwise.subby.cloud/prepared.json`
   with `curl`, the public note the night's preparation writes (04:17 UTC,
   `picwise-prepare.timer`). The site answers from the last prepared file only until it
   is 30 hours old (`PICWISE_PREPARED_MAX_AGE_HOURS`); then it shows no product, and
   nothing else tells anyone. The report puts first, before anything else, any of:
   - `"prepared"` not `true`: the night failed (its `reason`); such a note carries no
     `prepared_at`, and the site still answers from the file before it, until that one
     is 30 hours old;
   - `prepared_at` missing, or more than 30 hours before the time it was read (also when
     the note itself was not rewritten: then `written_at` is old too);
   - in `intake_change`, a shop under `shrunk` (fewer than half the night before's rows)
     or `gone`, with its rows before and now. A note written before `249cc06` was
     deployed has no `intake_change`: say it is not there yet.
   The note, never a link from it; the time it was read, in UTC. An email from the
   server itself when the night fails is not built: it needs the owner's choice of
   address and sender.
   **The server's health** (owner, 2026-11-16, among the proposals for the daily work:
   «Έλεγχος προσφορών, ταχύτητας και πόρων ... Ειδοποίηση μόνο αν ξεπεράσουν το όριο»):
   at the start of the day, start `.github/workflows/server-health.yml` by hand (the GitHub
   tools: run the workflow, on `main`; it only reads, and takes about half a minute), then
   read that run (the workflow's runs, then its job's log). Its own schedule, 08:07 UTC,
   is not waited for: GitHub started it 9 to 10 hours late on 16, 17 and 18/11 (17:09 to
   18:20 UTC), after the daily session; it stays as a second look in the evening, and as
   the only one on a day whose session does not run. On a Sunday the run started by hand
   counts the week's searches that found no product too (the workflow does on Sundays).
   When starting it fails, read its last run and say how old it is. Its step "What
   runs on the server, and which limit is passed" ends with each limit passed, "over the
   limit: …", or with "within every limit". The limits are in
   `deployment/server/print_health.py`: the site's service not active; the night's
   preparation failed, or the catalogue prepared more than 30 hours before, or a shop lost
   or shrunk to less than half; the offers fetched more than 30 hours before, or their
   last fetch failed; the photos checked more than 30 hours before; the site's memory and
   the preparation's peak together over 20 GB (of the server's 24; 18 until 19/11), less than 4 GB
   available, the preparation longer than 30 minutes; less than 20 GB of disk free;
   yesterday's AI spend at its cap. Its step "How fast the site answers, from outside"
   gives each page's first byte and the server's part of it: a page not answering 200, or
   a search whose server's part is over 1 s also when asked again, passes the limit of
   speed. Each limit passed goes first in the report, one line each, in plain words; the
   rest of the log is told only on Sundays. When the run failed, the report says so first.
   **Whether the Sunday tidy-up of the branches ran** (owner, 2026-11-16: «Θέλω να
   λαμβάνω ενημέρωση να συμπεριλάβεις την αυτόματη εργασία»): on a Sunday, and on the
   first day after one whose session did not report it, read the last run of
   `.github/workflows/tidy-branches.yml` (scheduled Sundays 03:17 UTC; the GitHub tools:
   the workflow's runs, then its job's log, whose last line reads "== N deleted, M kept").
   The report gives it one line: when it ran, how many branches it deleted and kept, the
   name of any branch "kept, a commit found nowhere else"; or that it failed or did not
   run, which the report puts first. The first such run, 22/11, should delete pull
   request #23's branch `ccr-99b47f03-l8t4dj` (owner, 16/11): say whether it did.
3. **Work.** The next step of the handoff's "START HERE", in small, closed steps: fix
   by cause, never word by word; every fix with its tests; the measures before and
   after (`deployment/server/print_search_reading.py` offline and free; the server's
   catalogue through the read-only workflows, `search-audit.yml` and the others, the AI at
   most **$2 a day** in all); record each step in the handoff's first section and in
   `PROGRESS.md`; push each commit to the session's branch and to `ccr-4f47068a-99ikwe`
   (the owner's standing word, 2026-11-07).
4. **Report.** The session's last message is the email: in Greek, short, plain words
   (the owner reads it on a phone). First, always, whatever failed or passed a limit (the
   night's preparation, the server's health, the Sunday tidy-up), one line each. Then:
   - **A quiet day** (owner, 2026-11-16: «Ήσυχες μέρες: μία γραμμή ... Όταν δεν συμβαίνει
     τίποτα, το καθημερινό email είναι μία γραμμή «όλα εντάξει». Τα προβλήματα έρχονται
     πάντα πρώτα»): nothing failed or passed a limit, nothing is proposed to go on the
     site and no question waits for the owner. The email is one line: «Όλα εντάξει.»,
     with the day's work in a few words on the same line when there was some («Όλα
     εντάξει. Σήμερα: …»).
   - **Any other day:** what was done; the numbers before and after; what is proposed to
     go on the site, ending with «Να το ανεβάσω;»; the questions that need the owner, each
     one line; what comes next.
   - **On Sundays, the week's summary** in place of the day's report, after the day's
     problems (owner, 2026-11-16: «Εβδομαδιαία σύνοψη Κυριακής: Τι έγινε την εβδομάδα,
     κατάλογος, τιμές (▼/▲), αναζητήσεις επισκεπτών (συχνές και χωρίς αποτέλεσμα),
     ταχύτητα και πόροι του διακομιστή, καθάρισμα κλάδων, εκκρεμότητες»), a line or two
     each:
     - the week's work: what went on the site, what waits for a «ναι» (`PROGRESS.md`);
     - the catalogue: products and shops now and a week before (the `prepared:` line of
       today's run of `server-health.yml` and of the run 7 days before), the shops gone,
       shrunk or new in the week (each day's "shops since the preparation before");
     - the prices: today's "price notes" (▼ down, ▲ up) and the prices changed in the
       week (each day's "prices changed tonight", added up);
     - the visitors' searches: how many in the week, how many different, how many times
       the most searched one, how many found no product (the Sunday run's two lines).
       Their words are not in the log, which is public like the repository, and are never
       printed there; showing them to the owner needs a private way, which is the owner's
       decision (proposed in the first Sunday summary, 22/11);
     - speed and resources, from the week's runs of `server-health.yml`: the slowest
       search (the server's part), the highest memory at night, the longest preparation,
       the disk free, the AI's spend;
     - the Sunday tidy-up of the branches (above);
     - what waits for the owner: each open question, one line.
   No link to a shop, no secret, nothing invented, nothing claimed that was not checked.
   Then, every day, even when nothing was done, the session calls `PushNotification` with
   a short Greek summary of the report: the email and the phone notification go out only
   through it (2026-11-08: a session that skipped it left the owner without the day's
   email; the scheduled task's prompt says so too, its step 6).
5. **The owner's answer.** «ναι» or «ανέβασε» to what the report proposed: deploy it
   (push the commit the report named, its tests passed, to `ccr-1361f1a7-dcpo60`), follow
   the deployment's run to its end, read its log, record it, and go on with the work.
   «όχι»: nothing goes on the site; record it. Any other answer is the owner's
   instruction. No answer: nothing goes on the site; the next day's session goes on with
   the work and asks again.

## What the session does on its own

- Fixes of the search's rules and the code around them, with their tests; the measures
  within the day's AI limit; reading the server's state through the read-only
  workflows; the records.
- Turning a measure's workflow on and off again in one commit each, as its file says.

## What it always asks first, in the report, and waits for

- **Anything going on the site:** at most once a day, and only after the owner's «ναι»
  or «ανέβασε» to that day's report.
- AI spending over $2 in a day; any other cost.
- Any change to `PROJECT_RULES.md`, `docs/MISSION.md`, the Decision Contract or another
  rule or contract; to what is shown or how products are ordered or recommended, beyond
  what a rule already decided says.
- The privacy page and every legal text.
- Google: what is given to it, indexed or submitted.
- Shops, networks and Awin: programmes, tokens, the feed; never ask for the feed link (it
  holds the key); never open an Awin tracked link; never propose contacting the shops.
- The cloud environment, secrets (only in GitHub's or Vercel's secrets), Supabase, the
  server's setup; `main` (nothing on it without the owner's «ναι»); deleting anything
  kept. The weekly tidy-up of the branches (`tidy-branches.yml`, owner, 2026-11-15:
  «Ναι, το εγκρίνω») is approved as it is; changing what it deletes or keeps is asked
  first.

## When it stops and only reports

- A test that passed before fails, or a measure comes out worse, or a workflow fails, or
  the server or the site shows something unexpected: nothing goes on the site; the report
  says what was seen.
- The owner says «σταμάτα»: the scheduled task is turned off.
