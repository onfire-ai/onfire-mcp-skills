# Top 5 Plays - Candidate Library

Each play includes a trigger condition (what data finding activates it), a problem statement template, an Onfire action, and an expected outcome. The skill selects the 5 most impactful plays based on what was actually found in the data.

---

## Play: Buying Committee Expansion

**Trigger**: Single-threaded accounts found in Step 5 (only 1 contact per account), especially accounts in mid or late pipeline stages.

**Problem template**:
> X accounts in active pipeline have only 1 known contact in the CRM. Single-threaded deals are N× more likely to stall or be lost when that contact goes dark, changes roles, or is not the actual decision maker.

**Onfire Action**:
Use Onfire `search_people` to find additional buying committee members at these accounts. Filter for Economic Buyer and Technical Evaluator personas. Add the top 2-3 contacts per account to the CRM and enroll them in a targeted sequence.

**Expected Outcome**:
Multi-threaded accounts have 30-40% higher win rates. Prioritize the X accounts currently in late-stage pipeline first.

---

## Play: Pipeline Whitespace from Intent

**Trigger**: High-intent Onfire accounts identified in Step 7 that do not appear in the CRM pipeline at all.

**Problem template**:
> Onfire signals show X companies in your target market with active buying intent that have no open opportunity in your CRM. These accounts are evaluating solutions now.

**Onfire Action**:
Use Onfire intent data to prioritize these accounts for immediate outbound. Pull the top decision makers at each account using `search_people` and create new opportunities in Salesforce with the enriched contacts attached.

**Expected Outcome**:
Injecting intent-qualified accounts into pipeline reduces average sales cycle by 20-30% compared to cold outbound.

---

## Play: Persona Targeting Fix

**Trigger**: Persona distribution in Step 6 shows Champion-heavy or Economic Buyer-thin distribution.

**Problem template**:
> X% of CRM contacts are Champion-level roles (practitioners). Economic Buyers - the people who sign the contract - represent only Y% of contacts. This means deals are being built from the bottom up, which lengthens sales cycles and increases loss risk at the approval stage.

**Onfire Action**:
Use Onfire `search_people` with Economic Buyer persona filters to find VP/C-suite contacts at existing accounts. For each account missing an Economic Buyer, add the top-scoring candidate from Onfire and assign them to a separate executive outreach sequence.

**Expected Outcome**:
Introducing an Economic Buyer contact into late-stage deals reduces average close time and improves forecast accuracy.

---

## Play: Stalled Deal Revival

**Trigger**: Stalled deals found in Step 4 (no activity in 14+ days), especially those with ARR above average deal size.

**Problem template**:
> X open opportunities have had no recorded activity in the last 14+ days, representing $Y in pipeline. Deals that go dark for 2+ weeks have a significantly higher probability of being lost silently rather than formally closed.

**Onfire Action**:
For each stalled deal, use Onfire data to find a new contact at the account who has not been engaged before - ideally at a different seniority level than existing contacts. Use this as a re-entry point to restart the conversation with fresh context.

**Expected Outcome**:
Re-engaging stalled deals through a new contact has a higher response rate than following up with an unresponsive existing contact. Even reviving 20% of stalled pipeline has significant ARR impact.

---

## Play: Inbound Lead Prioritization

**Trigger**: Inbound motion shows low conversion rate in Step 4, or inbound leads/opps with no recent activity.

**Problem template**:
> Your inbound motion generates X leads/opportunities but converts at only Y% - below the benchmark for inbound of 20-30%. The likely cause is undifferentiated follow-up: all inbound leads receive the same sequence regardless of company fit or intent level.

**Onfire Action**:
Enrich inbound leads with Onfire firmographic and intent data on arrival. Score each lead by ICP fit (industry, size, persona) and intent signal strength. Route the top 20% to immediate personal outreach from AEs. Route the rest to automated nurture.

**Expected Outcome**:
Prioritizing the top 20% of inbound by fit + intent typically recovers 40-60% of the conversion gap without increasing volume.

---

## Play: Late-Stage Multi-Thread Fast

**Trigger**: Accounts in the final 1-2 pipeline stages with only 1-2 contacts and deal value above threshold.

**Problem template**:
> X deals in final pipeline stages represent $Y in near-term revenue but have only Z contacts on record. A single-threaded late-stage deal is the highest-risk scenario: one person going silent can stall or kill a deal that is otherwise ready to close.

**Onfire Action**:
Immediately find 2-3 additional contacts at these accounts using Onfire. Focus on: (1) the Economic Buyer if not already in CRM, (2) a procurement or legal contact who will need to be involved in signing anyway. Get ahead of blockers before they appear.

**Expected Outcome**:
Reducing late-stage deal risk on high-ARR accounts has direct impact on quarterly forecast accuracy and close rate.

---

## Play: ICP Scoring and Prioritization

**Trigger**: Many accounts with unknown or unclear CRM status but Onfire shows high intent score.

**Problem template**:
> X accounts in the CRM have no clear pipeline status or owner, but Onfire intent signals show active research behavior. These accounts are warm but being treated as cold due to lack of CRM hygiene.

**Onfire Action**:
Use Onfire intent scores to rank all unowned/unstatused accounts. Assign the top X to AEs with a specific outreach prompt tied to their intent signal (e.g. "they are researching [topic] right now"). Update CRM status fields for these accounts.

**Expected Outcome**:
Working intent-warm accounts with no pipeline attachment is one of the highest-ROI prospecting motions available.
