# EduPath — End-User & Administrator Guide
**System:** EduPath — Personalized Tutoring Agent\
**Academic Project:** CSE473 Major Project\
**Author:** Perla Manikanta

---

## 1. Getting Started as a Learner

### Step 1: Sign in with Google
1. Open the EduPath application URL in your browser.
2. Click **"Continue with Google"** on the sign-in page.
3. Authenticate with your college or personal Google account.

### Step 2: Confirm Age Requirement
- EduPath currently supports adult learners (18+).
- Review the notice and check *"I confirm that I am 18 years of age or older"*, then click **"Continue to EduPath"**.

### Step 3: Configure Your Learning Profile
1. Select **"Learner Profile"** from the sidebar navigation.
2. Choose your current **Proficiency Level**:
   - *Beginner:* Simple analogies, gentle pace, core concepts.
   - *Intermediate:* Code-first, step-by-step logic, common error patterns.
   - *Advanced:* Deep reasoning, edge cases, algorithmic challenges.
3. Choose your **Explanation Style** (*Simple*, *Step by Step*, or *Example First*).
4. Set your **Daily Study Availability** (e.g. 45 minutes) and state your **Learning Goal**.
5. Click **"Save Profile Changes"**.

### Step 4: Take the Diagnostic Assessment
1. Select **"Python Assessment"** from the sidebar.
2. Choose **"Diagnostic"** to evaluate your baseline knowledge across all 9 topics.
3. Answer each multiple-choice question and submit the assessment.
4. Your score, topic-by-topic accuracy, and mastery indicators update automatically!

### Step 5: Follow Your Personalized Study Plan
1. Select **"Study Plan"** to review your generated curriculum schedule.
2. Topics where you scored $<50\%$ are prioritized for **Targeted Revision**.
3. Topics with strong performance are scheduled for **Spaced Review**.
4. Mark activities complete as you study to watch your progress bar advance.

### Step 6: Chat with Your AI Tutor
1. Select **"AI Tutor"** from the sidebar.
2. Ask any Python programming question (e.g. *"How does range work in a for loop?"*).
3. The tutor retrieves relevant curriculum knowledge-base material, injects few-shot examples calibrated to your proficiency level, and explains the concept with verified citations (`[S1]`, `[S2]`).
4. Click on **"Sources"** to inspect the exact textbook title, page number, and retrieval similarity score.
5. Provide feedback by clicking 👍 or 👎 on any assistant response.

---

## 2. Administrator Guide (Knowledge Management)
Users with the `admin` role have access to elevated workspace tabs:
1. **Knowledge Management:**
   - Upload new course documents (PDF, TXT, MD).
   - Review SHA-256 duplicate detection and rights metadata.
   - Trigger the **Resumable Batch Embedding** action to generate 768-dimensional Gemini vectors.
   - Manage course publication status (`is_published`).
2. **AI Tutor Feedback:**
   - Review aggregated learner ratings (thumbs up/down) to detect confusing responses.
3. **AI Tutor Operations:**
   - Inspect agent run duration, latency percentiles, and token consumption telemetry.
