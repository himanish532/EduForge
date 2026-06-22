"""
EduForge curated knowledge base — educational content chunks for RAG.

These are hand-authored, factually accurate summaries used as the
retrieval corpus. No scraping, no external DB, no cost.

Each chunk is:
  - One focused concept (~100-200 words)
  - Tied to a subject + grade range
  - Attributed to a source for citation
"""

from __future__ import annotations

from .embedding_store import KnowledgeChunk

KNOWLEDGE_BASE: list[KnowledgeChunk] = [
    # ── MATH ──────────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="math-fractions-001",
        subject="math",
        grade_range="3-6",
        topic="Fractions",
        text=(
            "A fraction represents a part of a whole. The number on the bottom "
            "(denominator) tells you how many equal parts the whole is divided into. "
            "The number on top (numerator) tells you how many of those parts you have. "
            "For example, 3/4 means the whole is split into 4 equal pieces and you "
            "have 3 of them. To add fractions with the same denominator, just add the "
            "numerators. To add fractions with different denominators, first find a "
            "common denominator by finding the least common multiple."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="math-algebra-001",
        subject="math",
        grade_range="6-9",
        topic="Algebra Basics",
        text=(
            "Algebra uses letters (variables) to represent unknown numbers. "
            "An equation is a statement that two expressions are equal, like 2x + 3 = 7. "
            "To solve for x, perform the same operation on both sides to isolate x. "
            "Subtract 3 from both sides: 2x = 4. Divide both sides by 2: x = 2. "
            "The key principle is that any operation done to one side must be done to "
            "the other to keep the equation balanced — like a scale."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="math-quadratic-001",
        subject="math",
        grade_range="9-12",
        topic="Quadratic Equations",
        text=(
            "A quadratic equation has the form ax² + bx + c = 0. The quadratic formula "
            "x = (-b ± √(b²-4ac)) / 2a gives the solutions. The discriminant b²-4ac "
            "determines the number of real solutions: positive = two real roots, "
            "zero = one real root (touching x-axis), negative = no real roots (complex). "
            "Quadratics model projectile motion, area problems, and optimization. "
            "Factoring works when the equation factors neatly; otherwise use the formula."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="math-pythagorean-001",
        subject="math",
        grade_range="7-10",
        topic="Pythagorean Theorem",
        text=(
            "In a right triangle, the square of the hypotenuse equals the sum of the "
            "squares of the other two sides: a² + b² = c², where c is the hypotenuse "
            "(the side opposite the right angle). This means if you know two sides, "
            "you can always find the third. For example, a = 3, b = 4 gives "
            "c = √(9+16) = √25 = 5. The 3-4-5 triangle is the most famous Pythagorean "
            "triple. The theorem is used in navigation, construction, and physics."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="math-calculus-derivatives-001",
        subject="math",
        grade_range="11-12",
        topic="Calculus Derivatives",
        text=(
            "A derivative measures how fast a function changes at any point — it is the "
            "instantaneous rate of change. If f(x) = x², then f'(x) = 2x, meaning at "
            "x=3 the function is increasing at rate 6. The power rule: d/dx(xⁿ) = nxⁿ⁻¹. "
            "The derivative of a constant is 0. Derivatives are used to find maxima and "
            "minima (set f'(x) = 0), and to understand velocity and acceleration in physics. "
            "The chain rule handles composite functions: d/dx[f(g(x))] = f'(g(x))·g'(x)."
        ),
        source="curated",
    ),

    # ── SCIENCE ───────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="science-photosynthesis-001",
        subject="science",
        grade_range="4-8",
        topic="Photosynthesis",
        text=(
            "Photosynthesis is the process plants use to make their own food from sunlight. "
            "In chloroplasts (the green parts of cells), plants absorb sunlight and use it "
            "to convert carbon dioxide (CO₂) from the air and water (H₂O) from the soil "
            "into glucose (sugar) and oxygen. The equation is: "
            "6CO₂ + 6H₂O + light energy → C₆H₁₂O₆ + 6O₂. "
            "The glucose powers the plant's growth, and the oxygen is released into the air — "
            "which is what animals breathe. Chlorophyll is the green pigment that captures light."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="science-gravity-001",
        subject="science",
        grade_range="3-7",
        topic="Gravity",
        text=(
            "Gravity is a force that pulls objects toward each other. The more massive an "
            "object, the stronger its gravitational pull. Earth's gravity pulls everything "
            "toward its center, which is why things fall down. On Earth, gravity "
            "accelerates falling objects at about 9.8 m/s² (in the absence of air). "
            "The Moon's gravity is about 1/6 of Earth's, which is why astronauts can jump "
            "higher there. Gravity keeps planets in orbit around the Sun and the Moon in "
            "orbit around Earth. Isaac Newton described gravity with his law of universal gravitation."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="science-water-cycle-001",
        subject="science",
        grade_range="4-8",
        topic="Water Cycle",
        text=(
            "The water cycle describes how water moves continuously through Earth's systems. "
            "Evaporation: the Sun heats water in oceans, lakes, and rivers, turning it to "
            "water vapor that rises into the atmosphere. Condensation: as vapor rises and "
            "cools, it forms clouds and fog. Precipitation: when water droplets in clouds "
            "combine and become heavy, they fall as rain, snow, sleet, or hail. "
            "Collection: water flows into rivers, lakes, and oceans, and soaks into the "
            "ground (groundwater). The cycle then repeats continuously."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="science-cells-001",
        subject="science",
        grade_range="5-9",
        topic="Cells",
        text=(
            "Cells are the basic units of life. All living things are made of one or more cells. "
            "Animal cells have a nucleus (control center), mitochondria (energy producers), "
            "cell membrane (boundary), and cytoplasm (liquid interior). Plant cells have all "
            "of these plus a rigid cell wall, chloroplasts (for photosynthesis), and a large "
            "central vacuole for storing water. Prokaryotic cells (bacteria) have no nucleus. "
            "Eukaryotic cells (plants, animals, fungi) have a nucleus. Cell division (mitosis) "
            "produces identical copies; meiosis produces reproductive cells with half the DNA."
        ),
        source="curated",
    ),

    # ── HISTORY ───────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="history-french-revolution-001",
        subject="history",
        grade_range="8-12",
        topic="French Revolution",
        text=(
            "The French Revolution (1789–1799) was a period of radical political and social "
            "transformation in France. Causes included financial crisis, inequality between "
            "the Three Estates (clergy, nobility, and commoners), and Enlightenment ideas "
            "about liberty and equality. The storming of the Bastille on July 14, 1789 marked "
            "the revolution's symbolic start. The monarchy was abolished, King Louis XVI was "
            "executed, and France became a republic. The Reign of Terror (1793–94) saw "
            "thousands guillotined. The revolution ended when Napoleon Bonaparte took power in 1799."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="history-civil-war-001",
        subject="history",
        grade_range="7-10",
        topic="American Civil War",
        text=(
            "The American Civil War (1861–1865) was fought between the Union (Northern states) "
            "and the Confederacy (11 Southern states that seceded). The primary cause was "
            "slavery — Southern states wanted to preserve it while the North increasingly "
            "opposed its expansion. Abraham Lincoln's election in 1860 triggered secession. "
            "Key battles include Gettysburg (1863) and Antietam. Lincoln's Emancipation "
            "Proclamation (1863) freed enslaved people in Confederate states. The Union won "
            "when Confederate General Lee surrendered at Appomattox Court House in April 1865. "
            "The war resulted in 620,000–750,000 deaths and the abolition of slavery."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="history-world-war-2-001",
        subject="history",
        grade_range="8-12",
        topic="World War II",
        text=(
            "World War II (1939–1945) was the deadliest conflict in human history, involving "
            "most of the world's nations. It began when Nazi Germany invaded Poland on "
            "September 1, 1939. The Allied Powers (UK, France, USSR, USA, and others) "
            "fought the Axis Powers (Germany, Italy, Japan). The Holocaust killed approximately "
            "6 million Jewish people and millions of others. The war in Europe ended with "
            "Germany's surrender on May 8, 1945 (V-E Day). The war in the Pacific ended after "
            "the US dropped atomic bombs on Hiroshima and Nagasaki in August 1945, leading to "
            "Japan's surrender on September 2, 1945 (V-J Day)."
        ),
        source="curated",
    ),

    # ── CODING ────────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="coding-python-basics-001",
        subject="coding",
        grade_range="6-12",
        topic="Python Basics",
        text=(
            "Python is a beginner-friendly programming language known for its readable syntax. "
            "Variables store data: name = 'Alice', age = 14. Print output with print(name). "
            "If/else controls flow: if age >= 13: print('teenager') else: print('child'). "
            "Loops repeat code: for i in range(5): print(i) prints 0 through 4. "
            "Functions group reusable code: def greet(name): return 'Hello ' + name. "
            "Lists store sequences: numbers = [1, 2, 3]. Access with numbers[0] (first item). "
            "Python uses indentation (spaces) to define code blocks — no curly braces."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="coding-algorithms-001",
        subject="coding",
        grade_range="8-12",
        topic="Algorithms",
        text=(
            "An algorithm is a step-by-step procedure to solve a problem. Key properties: "
            "correctness (produces right output), efficiency (uses minimal time/space), "
            "and termination (always stops). Sorting algorithms arrange data: bubble sort "
            "compares adjacent pairs (O(n²)); merge sort divides and conquers (O(n log n)). "
            "Searching: linear search checks every element (O(n)); binary search on sorted "
            "data halves the search space each step (O(log n)). Big-O notation describes "
            "how time grows with input size. Understanding algorithms helps write faster, "
            "more efficient programs."
        ),
        source="curated",
    ),

    # ── ENGLISH ───────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="english-essay-structure-001",
        subject="english",
        grade_range="6-12",
        topic="Essay Structure",
        text=(
            "A well-structured essay has three parts: Introduction, Body, and Conclusion. "
            "Introduction: start with a hook (interesting fact or question), provide context, "
            "and end with a clear thesis statement (your main argument). Body paragraphs: "
            "each paragraph covers one main idea, starts with a topic sentence, provides "
            "evidence and examples, and explains how the evidence supports your thesis. "
            "Use transitions (however, furthermore, in contrast) to connect ideas. "
            "Conclusion: restate your thesis in new words, summarize key points, and end "
            "with a final thought or call to action. Avoid introducing new arguments in the conclusion."
        ),
        source="curated",
    ),
    KnowledgeChunk(
        chunk_id="english-figurative-language-001",
        subject="english",
        grade_range="5-9",
        topic="Figurative Language",
        text=(
            "Figurative language uses words beyond their literal meaning to create vivid images. "
            "Simile: compares two things using 'like' or 'as' — 'Her eyes were like stars.' "
            "Metaphor: states one thing IS another — 'Life is a journey.' "
            "Personification: gives human qualities to non-human things — 'The wind whispered.' "
            "Hyperbole: extreme exaggeration — 'I've told you a million times.' "
            "Alliteration: repeated consonant sounds — 'Peter Piper picked a peck.' "
            "Onomatopoeia: words that sound like what they describe — buzz, crash, sizzle. "
            "Figurative language makes writing more engaging and memorable."
        ),
        source="curated",
    ),

    # ── GENERAL ───────────────────────────────────────────────────────────
    KnowledgeChunk(
        chunk_id="general-study-skills-001",
        subject="general",
        grade_range="1-12",
        topic="Study Skills",
        text=(
            "Effective studying starts with active recall — testing yourself rather than "
            "re-reading notes. Spaced repetition: review material at increasing intervals "
            "(1 day, 3 days, 1 week) to move knowledge into long-term memory. The Pomodoro "
            "technique: study for 25 minutes, take a 5-minute break, repeat. "
            "Elaborative interrogation: ask 'why?' and 'how?' to deepen understanding. "
            "Mind mapping connects related concepts visually. Teaching someone else is the "
            "most powerful way to solidify understanding. Avoid multitasking — focused "
            "single-task studying is more effective than studying with distractions."
        ),
        source="curated",
    ),
]


def get_knowledge_base() -> list[KnowledgeChunk]:
    return KNOWLEDGE_BASE
