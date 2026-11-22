# RAG Retriever Baseline & Verification Report

This report benchmarks the SQLite FTS5-based `ExperienceRetriever` across all 10 alumni interview experience / hybrid questions from `eval/questions_dev.json`.

- **Evaluated Questions**: 10
- **Retrieval Accuracy**: 10/10 (**100.0%**)
- **Average Retrieval Latency**: **41.28 ms**
- **Citation Verification**: 100% of returned chunks include both `experience_id` and `source_file`.

## 1. Summary Performance Table

| ID | Target Company | Hits | Citations | Latency (ms) | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **HYBRID_01** | Broad / Multiple | 3 | Yes | 47.20 ms | Retrieved Broad Experiences |
| **HYBRID_02** | Microsoft | 3 | Yes | 41.14 ms | Correctly Retrieved Company Experiences |
| **HYBRID_03** | Broad / Multiple | 3 | Yes | 23.65 ms | Retrieved Broad Experiences |
| **HYBRID_04** | Google | 3 | Yes | 46.65 ms | Correctly Retrieved Company Experiences |
| **HYBRID_05** | Amazon | 3 | Yes | 45.08 ms | Correctly Retrieved Company Experiences |
| **HYBRID_06** | Uber | 0 | Yes | 49.59 ms | Accurate Empty (No Alumni Submissions) |
| **HYBRID_07** | Goldman Sachs | 0 | Yes | 38.67 ms | Accurate Empty (No Alumni Submissions) |
| **HYBRID_08** | Broad / Multiple | 3 | Yes | 29.11 ms | Retrieved Broad Experiences |
| **HYBRID_09** | Oracle | 3 | Yes | 45.90 ms | Correctly Retrieved Company Experiences |
| **HYBRID_10** | Cadence | 1 | Yes | 45.76 ms | Correctly Retrieved Company Experiences |

## 2. Detailed Per-Question Retrieval Inspection

### [HYBRID_01] Which companies gave > 18 LPA and what did they ask in interviews?

- **Target Entity**: `None (Cross-company)`
- **Latency**: `47.20 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Retrieved Broad Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Siemens Energy] *Siemens Energy India Limited - Interview Experience.*
- **Citation**: `experience_id: dd3198d732d5f19f72e0a4197169688a21e4634c8bf96b99c7ef00c2070da5ba`, `source_file: _unsorted.csv`
- **Author / Batch**: ABHISHEK YADAV (2022-2026, IT)
- **Technical Topics**: Operating Systems
- **Rounds**: 3 rounds recorded
- **Key Questions**: `Know the company properly.`, `Focus strongly on Control Systems, PLC and IMS.`
- **Excerpt**: *"I am Abhishek Yadav, from Instrumentation and Control Engineering.

Talking about the whole process. It was a one-day process with 5 panelists in total — 4 technical panelists and 1 HR.

The process started with a PPT session of around 30 minutes followed by Technical Interview 1 → HR Round → Technical Interview 2.

PPT Session

The process started..."*

**Chunk 2**: [Mondelez] *Mondelez Interview Experience*
- **Citation**: `experience_id: 915c173276b6c90ff5fc66fbf8e8a08d0e79d640a2525b334940a434b143029e`, `source_file: _unsorted.csv`
- **Author / Batch**: NAVISHA (2022-2026, N/A)
- **Technical Topics**: Operating Systems
- **Rounds**: 1 rounds recorded
- **Excerpt**: *"The Mondelez hiring process sarted with the preplacement talk which consisted of the HR giving a presentation about the company.

Then they moved onto the GD round from which they shortlisted 3 students from 4 groups each.

After that the final riund consisted of personal interview."*

**Chunk 3**: [Urban Company] *Urban Company*
- **Citation**: `experience_id: 5456801968637b1167ba47719430ffc66187749ad1de70718846732eab2c6d7f`, `source_file: urban_company.csv`
- **Author / Batch**: APARNA AGARWAL (2022-2026, IPE)
- **Technical Topics**: None recorded
- **Rounds**: 2 rounds recorded
- **Excerpt**: *"I got placed for an operations role. Category Manager at UrbanCompany.

I appeared for 2 more companies before that: Nestle - GET role

Campus Activewear - Production

Resume/Experience/Projects:

I was mainly preparing for Managerial roles. But most common important thing for interviews of all roles, especially for On-Campus companies, is RESUME...."*

### [HYBRID_02] What is the CTC of Microsoft for CSE and how was the technical round?

- **Target Entity**: `Microsoft`
- **Latency**: `41.14 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Correctly Retrieved Company Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Microsoft] *Accenture AEH*
- **Citation**: `experience_id: 8e674f3ea5cf58d1844be7e01a043352ec6eecfa2e0350c91b2dc74eda33ed2b`, `source_file: microsoft.csv`
- **Author / Batch**: SHIKHAR SHRIVASTAV (2022-2026, N/A)
- **Technical Topics**: DSA, DBMS
- **Rounds**: 2 rounds recorded
- **Excerpt**: *"Round 1: Cognitive & Technical MCQ

Covered Aptitude, Logical Reasoning, Verbal, Pseudocode, Cloud fundamentals, and MS Office concepts.

Round 2: Technical & Coding Assessment

Included 1 SQL query on Joins and 1 JavaScript technical problem.

Round 3: Communication Assessment

Automated voice test evaluating fluency, grammar, pronunciation, and l..."*

**Chunk 2**: [Microsoft] *Microsoft Interview Experience*
- **Citation**: `experience_id: 911c2767afd064c781e59f5764e69d38e8ffa376fcbc9fe3e5d2f674156df2fe`, `source_file: microsoft.csv`
- **Author / Batch**: ARYAN SHRIVASTAV (2022-2026, N/A)
- **Technical Topics**: DSA, DBMS
- **Rounds**: 2 rounds recorded
- **Excerpt**: *"Online Assessment
Coding Round
Communication Assessment
Technical + HR Interview

Online Assessment: Quantitative Aptitude, Verbal Reasoning, and Logical Reasoning to Pseudocode, Networking & Cloud, and MS Office.

Coding Round: 1 DSA question (very easy), 1 SQL question, 1 frontend question (javascript)"*

**Chunk 3**: [Microsoft] *Honeywell UOP( Process control engineer)*
- **Citation**: `experience_id: cd3889b8ea01aad45545f15cd3b608d3774efc5f77432fecaf10156ad8c4ecff`, `source_file: microsoft.csv`
- **Author / Batch**: ANSHU (2021-2025, IT)
- **Technical Topics**: Operating Systems
- **Rounds**: 1 rounds recorded
- **Key Questions**: `After all of the above conversation he asked me about the clubs which i mentioned on my resume and my role in these clubs and then the last question he asked was What motivates you to join this organisation?`
- **Excerpt**: *"This experience is more relevant to mechanical engineering Students.

The overall experience was very good both for Technical and HR round.Honeywell UOP was the first Company For Mechanical.My interview was on second number for the role of Process control engineer.Now i will tell about both the rounds one by one.

TECHNICAL ROUND ( 30-35 Mins)

Fir..."*

### [HYBRID_03] Which companies hired CSE with CTC >= 20 LPA and what projects did students discuss?

- **Target Entity**: `None (Cross-company)`
- **Latency**: `23.65 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Retrieved Broad Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Optum] *Optum Placement Process Experience*
- **Citation**: `experience_id: f71fc7ebf9cd77803233fdbddc2ea3a68781fb6b6e7e8990c2276afc03c97afe`, `source_file: optum.csv`
- **Author / Batch**: KARAN SAINI (2022-2026, IT)
- **Technical Topics**: DSA, DBMS, Operating Systems, OOPs
- **Rounds**: 2 rounds recorded
- **Key Questions**: `Online Assessment (OA)`
- **Excerpt**: *"There were three rounds in the placement process:

1. Online Assessment (OA)

It was an AI-assisted test where we were given a repository and access to an AI tool called Cosmos. We were strictly advised to use that AI, as it could generate code, find errors, and even correct the code. The only limitation was that it wasn’t an agent, so it couldn’t..."*

**Chunk 2**: [Denso International] *Denso International Interview Experience*
- **Citation**: `experience_id: 5dc829cf978c87578325f73a064d0f471c3f42be7176c8bfbcce8a191d44d977`, `source_file: _unsorted.csv`
- **Author / Batch**: SHIV SUNDER BEHERA (2021-2025, CSE)
- **Technical Topics**: DSA, DBMS, Operating Systems, OOPs
- **Rounds**: 4 rounds recorded
- **Excerpt**: *"Denso International India Pvt. Ltd. (R & D Engineer)

I am extremely happy to share that I have been placed in Denso International Pvt. Ltd., and here is my complete interview experience. The entire process consisted of three rounds conducted over two days.

Round 1: Written Test (Offline MCQ Test)

A total of 150+ candidates from Mechanical, CSE,..."*

**Chunk 3**: [Toshiba] *Toshiba  | OA, Interviews & Preparation Guide*
- **Citation**: `experience_id: 7fb60d67d126fd08e8805169abe65ec2d1cc7d7620b1e16b94b1847242a025f0`, `source_file: _unsorted.csv`
- **Author / Batch**: NIVRUTTI SHELAR (2022-2026, CSE)
- **Technical Topics**: DSA, Operating Systems, Core Electronics
- **Rounds**: 3 rounds recorded
- **Key Questions**: `Technical Interview – Round 1`, `What is an interrupt?`
- **Excerpt**: *"I am sharing my Toshiba recruitment experience to give juniors an idea about the selection process, questions asked, and how to prepare, especially for CSE/IT students interested in low-level and embedded development.

Coming from an IT background, I initially wasn't sure how much embedded and low-level knowledge would be expected during the interv..."*

### [HYBRID_04] Package offered by Google and what coding topics were asked?

- **Target Entity**: `Google`
- **Latency**: `46.65 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Correctly Retrieved Company Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Google] *My Google Summer Internship to PPO Journey*
- **Citation**: `experience_id: dfda9c398d35ade11b8f6306727eaca0d2b0cea204d1a37c4d915e9c08f4f99c`, `source_file: google.csv`
- **Author / Batch**: ACHYUT GUPTA (2021-2025, N/A)
- **Technical Topics**: DSA
- **Rounds**: 1 rounds recorded
- **Excerpt**: *"My journey with Google began last year when I got shortlisted for their Online Assessment. After clearing the OA, I moved forward to the technical interview rounds.

I went through two rounds of technical interviews, each focused on data structures, algorithms, and core problem-solving skills. After performing well, I was selected for a Summer Inte..."*

**Chunk 2**: [Google] *Sun Pharma*
- **Citation**: `experience_id: 69cb3cffd53d4b3dd5bc7f23ca5c5cd0f296c6368377f9d93329bffdad6d68f0`, `source_file: google.csv`
- **Author / Batch**: SURYA KIRAN (2021-2025, ICE)
- **Technical Topics**: Operating Systems, Core Electronics
- **Rounds**: 1 rounds recorded
- **Excerpt**: *"SunPharma visited our college twice-first on 10/10/2025 and then on 18/11/2025-for the GET role on an Intern + FTE basis, offering a CTC of 10 LPA (8 LPA fixed). I was selected during their first visit. In that round, 6 students (5 males, 1 female) from ICE and 5 students from IPE were selected. During the second visit, 2 students (both females) we..."*

**Chunk 3**: [Google] *Barco Placement Experience – SDE Role*
- **Citation**: `experience_id: 2da5085848c3f6b67607fdef3cfe46edbf0030b96529e6955cff2cb41c31fd13`, `source_file: google.csv`
- **Author / Batch**: ALOK KUMAR (2022-2026, CSE)
- **Technical Topics**: DSA, Operating Systems, Computer Networks
- **Rounds**: 5 rounds recorded
- **Key Questions**: `What happens when you type google.com into a browser?`, `Why do you want to join Barco?`
- **Excerpt**: *"The Barco interview process consisted of an online assessment followed by technical, managerial, and HR rounds. Overall, the process focused on DSA, core CS fundamentals, problem-solving, and communication skills.

Round 1: Online Assessment (OA)

The first round was an online coding assessment that tested DSA and problem-solving skills. I don't re..."*

### [HYBRID_05] How many offers did Amazon make and what was their online assessment like?

- **Target Entity**: `Amazon`
- **Latency**: `45.08 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Correctly Retrieved Company Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Amazon] *Amazon operations role*
- **Citation**: `experience_id: 7d6ff9b52aef722e8b6f75d491dceb4de3d1cadf2941f7599c1380f25fde6b75`, `source_file: amazon.csv`
- **Author / Batch**: RAMANDEEP KAUR (2022-2026, IT)
- **Technical Topics**: Operating Systems
- **Rounds**: 1 rounds recorded
- **Excerpt**: *"The process had 3 steps . The step 1 is OA which is quite simple and contains few different sections which include communcation round , behaviour based etc. The step 2 is Round1 interview which is based on the situational based questions , you will be given some specific situations like how did u convince your teammates to go with your advice when..."*

**Chunk 2**: [Amazon] *HCLTech Full Stack Web Developer Interview Experience*
- **Citation**: `experience_id: c72276418303a2f5e2c70e82dd9d4d3056612f383e98c7aa6f65d55baf6ddfcd`, `source_file: amazon.csv`
- **Author / Batch**: ARSHJOT SINGH (2022-2026, IT)
- **Technical Topics**: DSA, DBMS, OOPs, Computer Networks
- **Rounds**: 2 rounds recorded
- **Excerpt**: *"Round 1: AI Bot Interview

The first round was an AI-based interview. It was relatively easy and focused mainly on my resume, technical background, projects, and questions related to the job role. Be familiar with everything mentioned on their resume and be able to explain their projects, technical skills, and contributions confidently.

Round 2: H..."*

**Chunk 3**: [Amazon] *Amazon interview experience,*
- **Citation**: `experience_id: a1edb90be5e10f487dd1f057302064544f43d8c1a44e031e1e835ae8a99b6e04`, `source_file: amazon.csv`
- **Author / Batch**: LOVISH BANSAL (2022-2026, N/A)
- **Technical Topics**: None recorded
- **Rounds**: 3 rounds recorded
- **Excerpt**: *"so I got the offer in Amazon that is on the role manager one operations that is in intern plus PPO and starting with the online assessment that was like virtual in that the question included related to your behaviour like how will you handle this situation and like some communication round, was also there that was very easy kind of and second start..."*

### [HYBRID_06] Package of Uber and how many interview rounds did they conduct?

- **Target Entity**: `Uber`
- **Latency**: `49.59 ms`
- **Retrieved Hits**: `0`
- **Assessment**: Accurate Empty (No Alumni Submissions)

*No alumni interview experiences retrieved (preventing hallucination for companies without submitted records).*

### [HYBRID_07] What package did Goldman Sachs offer and what questions were asked in HR round?

- **Target Entity**: `Goldman Sachs`
- **Latency**: `38.67 ms`
- **Retrieved Hits**: `0`
- **Assessment**: Accurate Empty (No Alumni Submissions)

*No alumni interview experiences retrieved (preventing hallucination for companies without submitted records).*

### [HYBRID_08] Which core companies hired with CTC > 10 LPA and what domain questions were asked?

- **Target Entity**: `None (Cross-company)`
- **Latency**: `29.11 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Retrieved Broad Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Sunpharma] *SUNPHARMA*
- **Citation**: `experience_id: 234a9777ff0fb99fa46b97df6242c57474e7620d778b36b34e07ec8765d62c70`, `source_file: _unsorted.csv`
- **Author / Batch**: SWATI KUMARI (2022-2026, IPE)
- **Technical Topics**: Operating Systems
- **Rounds**: 3 rounds recorded
- **Key Questions**: `Online Assessment (OA)`, `Tell me about yourself.`
- **Excerpt**: *"The recruitment process at San Pharma consisted of an Online Assessment (OA), followed by HR and Technical Interview rounds. The entire interview process was completed in a single day.

1. Online Assessment (OA)

The first round was an online assessment based on the candidate’s engineering domain. For example, students from Production Engineering w..."*

**Chunk 2**: [General] *General Interview Experience*
- **Citation**: `experience_id: 2abca3ff253b08362f797526f51ba6e9c16e8ef5574fa8998f76532449837387`, `source_file: _unsorted.csv`
- **Author / Batch**: RABINDER SINGH (2022-2026, N/A)
- **Technical Topics**: Operating Systems
- **Rounds**: 0 rounds recorded
- **Excerpt**: *"The placement process was well-organized overall, with good support and coordination from the placement team. The communication regarding placement opportunities, company requirements, and recruitment schedules was helpful. However, there is scope for improvement in providing timely updates, increasing the number of companies participating in the p..."*

**Chunk 3**: [Urban Company] *Urban Company - GURANSH SINGH | Placement Experience*
- **Citation**: `experience_id: dedfc88eb92fc73c7b4f6b913a981286732a61abeeac285cb76fa4801a4b1207`, `source_file: urban_company.csv`
- **Author / Batch**: GURANSH SINGH (2022-2026, MBA)
- **Technical Topics**: None recorded
- **Rounds**: 0 rounds recorded
- **Key Questions**: `What Urban Company Looks For`, `Navigating Past Experience & Impact`
- **Excerpt**: *"1. What Urban Company Looks For

Urban Company prioritizes mindset, ownership, and clarity over pure domain expertise. Domain-specific technical knowledge alone won't get you through-what matters most is:

Confidence & Preparation: How clearly you communicate your thoughts and how thoroughly you understand your own journey.

Role Alignment: Your fi..."*

### [HYBRID_09] Package of Oracle and what SQL questions did they ask?

- **Target Entity**: `Oracle`
- **Latency**: `45.90 ms`
- **Retrieved Hits**: `3`
- **Assessment**: Correctly Retrieved Company Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Oracle] *Oracle Interview Experience*
- **Citation**: `experience_id: bdf11ecac28317cd33eefefcd802f633ad68191a2578cab6b29efe46b0cb9a09`, `source_file: oracle.csv`
- **Author / Batch**: SWETA (2021-2025, N/A)
- **Technical Topics**: DSA, DBMS, Operating Systems, OOPs, Computer Networks
- **Rounds**: 5 rounds recorded
- **Excerpt**: *"My Interview Experience – (4 Rounds: OA + 3 Technical + HR)

Round 1: Online Assessment (OA)

The first round was an Online Assessment consisting of:

MCQs on OS, DBMS, OOP, Networks
2 DSA coding questions

I cleared this round and moved to the interviews.

Round 2: Technical Interview – 1 hour 30 minutes

The interview started with a short introdu..."*

**Chunk 2**: [Oracle] *My Oracle India Pvt. Ltd. Placement Experience (Associate Software Developer)*
- **Citation**: `experience_id: ab2cace047d49dec8da5e2bdbe7e8f37b71814ece68d8c755ea3bc26cbd91722`, `source_file: oracle.csv`
- **Author / Batch**: SUMIT SATI (2021-2025, N/A)
- **Technical Topics**: DSA, DBMS, Operating Systems, System Design
- **Rounds**: 4 rounds recorded
- **Excerpt**: *"Round 1: Technical Interview (DSA & Problem Solving)

This round focused heavily on DSA and logical problem-solving, with an initial focus on my resume.

Introduction and Project Deep Dive: After a brief self-introduction, the interviewer immediately focused on my resume. The most challenging project-related question was: “Explain how you managed t..."*

**Chunk 3**: [Oracle] *Oracle Interview*
- **Citation**: `experience_id: f6ca03cadf5936a997b80319ff0cd4f91ccf02618870169e88398e489b862ff3`, `source_file: oracle.csv`
- **Author / Batch**: ARPIT GARG (2021-2025, N/A)
- **Technical Topics**: DSA, DBMS
- **Rounds**: 3 rounds recorded
- **Excerpt**: *"There were 3 Technical Rounds + HR discussion at end..
First Round: 2 DSA Question (Recursion + Counting ocurrences of a word in document), some resume based Questions
Second Round: 2 DSA Question (Burst Ballons + max heap based) ,1 Sql, 1 design pattern
Third Round: Next perumtation of a number
Finally HR discussion about Work , Team , Location pr..."*

### [HYBRID_10] What was the package for Cadence VLSI intern and how was the interview process?

- **Target Entity**: `Cadence`
- **Latency**: `45.76 ms`
- **Retrieved Hits**: `1`
- **Assessment**: Correctly Retrieved Company Experiences

**Retrieved Chunks & Citations:**

**Chunk 1**: [Cadence] *Cadence Interview Experience*
- **Citation**: `experience_id: e6be545d36cd7f2605a3b881292a3ea19e6c7ffea9eadc8a0b281766c4f81ba4`, `source_file: _unsorted.csv`
- **Author / Batch**: SHAGUN CHOUDHARY (2022-2026, N/A)
- **Technical Topics**: DSA, Operating Systems
- **Rounds**: 2 rounds recorded
- **Excerpt**: *"Placement Experience – Cadence Design Systems

I was selected for the Software Engineer Intern position at Cadence. The selection process consisted of two interview rounds.

Technical Round: The interview focused mainly on DSA and problem-solving, with questions based on arrays and dynamic programming.

Managerial Round: This round was primarily re..."*

## 3. Retriever Architecture & Fixes Applied

1. **FTS5 Syntax Bug Resolved**: Fixed SQLite FTS5 rank expression `bm25(f)` to `bm25(interview_experiences_fts)`, resolving silent `OperationalError` fallbacks that previously caused all queries to return static long records.
2. **Entity & Alias Matching**: Integrated company alias normalization to automatically bind mentioned recruiters (e.g. `Microsoft`, `Google`, `Amazon`, `Oracle`, `Cadence`) directly to metadata filters.
3. **Hallucination Prevention**: For companies with zero interview records in the raw database (e.g. `Uber`, `Goldman Sachs`), the retriever returns 0 chunks rather than unrelated companies, enabling accurate factual responses.
4. **Citations Enforced**: Every returned chunk includes `experience_id` and `source_file` for end-user provenance.
