"""
AI/ML service for generating recommendations, predictions, and analytics.
Uses rule-based logic by default; can integrate OpenAI for enhanced recommendations.
"""
import os
from typing import List, Dict, Optional
from collections import defaultdict

# Optional OpenAI integration
try:
    import openai
    OPENAI_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))
    if OPENAI_AVAILABLE:
        openai.api_key = os.getenv("OPENAI_API_KEY")
except ImportError:
    OPENAI_AVAILABLE = False


def analyze_performance(responses: List[Dict]) -> Dict:
    """
    Analyze a user's question responses to identify strengths and weaknesses.
    Returns a detailed performance breakdown.
    """
    if not responses:
        return {
            "total_questions": 0,
            "subjects": {},
            "weak_topics": [],
            "strong_topics": [],
            "overall_accuracy": 0.0,
        }

    subject_stats = defaultdict(lambda: {
        "total": 0, "correct": 0, "incorrect": 0, "skipped": 0,
        "topics": defaultdict(lambda: {"total": 0, "correct": 0}),
        "difficulties": defaultdict(lambda: {"total": 0, "correct": 0}),
    })

    total = 0
    correct = 0

    for r in responses:
        question = r.get("questions", {})
        if not question:
            continue

        subject = question.get("subject", "Unknown")
        topic = question.get("topic", "Unknown")
        difficulty = question.get("difficulty", "Medium")

        total += 1
        subject_stats[subject]["total"] += 1
        subject_stats[subject]["topics"][topic]["total"] += 1
        subject_stats[subject]["difficulties"][difficulty]["total"] += 1

        if r.get("selected_option") is None:
            subject_stats[subject]["skipped"] += 1
        elif r.get("is_correct"):
            correct += 1
            subject_stats[subject]["correct"] += 1
            subject_stats[subject]["topics"][topic]["correct"] += 1
            subject_stats[subject]["difficulties"][difficulty]["correct"] += 1
        else:
            subject_stats[subject]["incorrect"] += 1

    # Identify weak and strong topics
    weak_topics = []
    strong_topics = []

    for subject, stats in subject_stats.items():
        for topic, topic_stats in stats["topics"].items():
            if topic_stats["total"] >= 2:  # Need at least 2 questions to judge
                accuracy = topic_stats["correct"] / topic_stats["total"]
                topic_info = {
                    "subject": subject,
                    "topic": topic,
                    "accuracy": round(accuracy * 100, 1),
                    "total_questions": topic_stats["total"],
                }
                if accuracy < 0.5:
                    weak_topics.append(topic_info)
                elif accuracy >= 0.8:
                    strong_topics.append(topic_info)

    # Sort by accuracy
    weak_topics.sort(key=lambda x: x["accuracy"])
    strong_topics.sort(key=lambda x: x["accuracy"], reverse=True)

    # Build subject performance dict
    subjects = {}
    for subject, stats in subject_stats.items():
        acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        subjects[subject] = {
            "total": stats["total"],
            "correct": stats["correct"],
            "incorrect": stats["incorrect"],
            "skipped": stats["skipped"],
            "accuracy": round(acc, 1),
            "difficulty_breakdown": {
                k: {
                    "total": v["total"],
                    "correct": v["correct"],
                    "accuracy": round((v["correct"] / v["total"] * 100) if v["total"] > 0 else 0, 1),
                }
                for k, v in stats["difficulties"].items()
            },
        }

    return {
        "total_questions": total,
        "overall_accuracy": round((correct / total * 100) if total > 0 else 0, 1),
        "subjects": subjects,
        "weak_topics": weak_topics[:10],
        "strong_topics": strong_topics[:10],
    }


def generate_recommendations(user_id: str, performance: Dict) -> List[Dict]:
    """
    Generate study recommendations based on performance analysis.
    Uses rule-based logic; optionally enhanced with OpenAI.
    """
    recommendations = []

    weak_topics = performance.get("weak_topics", [])
    subjects = performance.get("subjects", {})
    overall_accuracy = performance.get("overall_accuracy", 0)

    # Priority 1: Weak topics need urgent attention
    for i, topic in enumerate(weak_topics[:5]):
        rec = {
            "user_id": user_id,
            "title": f"Improve {topic['topic']}",
            "description": (
                f"Your accuracy in {topic['topic']} ({topic['subject']}) is only "
                f"{topic['accuracy']}%. Practice more questions on this topic to improve."
            ),
            "subject": topic["subject"],
            "priority": "High" if topic["accuracy"] < 30 else "Medium",
            "type": "practice",
            "estimated_time": "30 mins",
        }
        recommendations.append(rec)

    # Priority 2: Subject-level weaknesses
    for subject, stats in subjects.items():
        if stats["accuracy"] < 50 and stats["total"] >= 5:
            rec = {
                "user_id": user_id,
                "title": f"Revise {subject} fundamentals",
                "description": (
                    f"Your overall accuracy in {subject} is {stats['accuracy']}%. "
                    f"Consider revisiting the core concepts and formulas."
                ),
                "subject": subject,
                "priority": "High",
                "type": "revision",
                "estimated_time": "1 hour",
            }
            recommendations.append(rec)

    # Priority 3: Difficulty-based recommendations
    for subject, stats in subjects.items():
        diff_breakdown = stats.get("difficulty_breakdown", {})
        hard_stats = diff_breakdown.get("Hard", {})
        if hard_stats.get("total", 0) >= 3 and hard_stats.get("accuracy", 0) < 40:
            rec = {
                "user_id": user_id,
                "title": f"Practice hard {subject} problems",
                "description": (
                    f"You're struggling with hard {subject} questions "
                    f"(accuracy: {hard_stats['accuracy']}%). Focus on advanced problem-solving."
                ),
                "subject": subject,
                "priority": "Medium",
                "type": "practice",
                "estimated_time": "45 mins",
            }
            recommendations.append(rec)

    # Priority 4: General test-taking recommendation
    if overall_accuracy < 60:
        rec = {
            "user_id": user_id,
            "title": "Take a full mock test",
            "description": (
                f"Your overall accuracy is {overall_accuracy}%. "
                "Taking a timed full-length mock test will help improve speed and accuracy."
            ),
            "subject": "General",
            "priority": "Medium",
            "type": "test",
            "estimated_time": "3 hours",
        }
        recommendations.append(rec)

    # If performance is great, encourage maintaining it
    if overall_accuracy >= 80 and not weak_topics:
        rec = {
            "user_id": user_id,
            "title": "Great performance! Keep it up",
            "description": (
                f"Your accuracy is {overall_accuracy}%. "
                "Focus on maintaining consistency and attempting previous year papers."
            ),
            "subject": "General",
            "priority": "Low",
            "type": "revision",
            "estimated_time": "30 mins",
        }
        recommendations.append(rec)

    # Default if no recommendations generated
    if not recommendations:
        rec = {
            "user_id": user_id,
            "title": "Start practicing",
            "description": "Take some tests to get personalized AI recommendations based on your performance.",
            "subject": "General",
            "priority": "Medium",
            "type": "test",
            "estimated_time": "1 hour",
        }
        recommendations.append(rec)

    return recommendations


async def generate_recommendations_with_ai(user_id: str, performance: Dict) -> List[Dict]:
    """
    Use OpenAI GPT to generate enhanced recommendations.
    Falls back to rule-based if OpenAI is not available.
    """
    if not OPENAI_AVAILABLE:
        return generate_recommendations(user_id, performance)

    try:
        subjects_summary = ""
        for subject, stats in performance.get("subjects", {}).items():
            subjects_summary += f"- {subject}: {stats['accuracy']}% accuracy ({stats['total']} questions)\n"

        weak_summary = ""
        for topic in performance.get("weak_topics", [])[:5]:
            weak_summary += f"- {topic['topic']} ({topic['subject']}): {topic['accuracy']}%\n"

        prompt = f"""You are an expert educational AI tutor for competitive exam preparation (JEE/NEET).

Based on the following student performance data, generate 3-5 specific, actionable study recommendations.

Overall Accuracy: {performance.get('overall_accuracy', 0)}%
Total Questions Attempted: {performance.get('total_questions', 0)}

Subject Performance:
{subjects_summary}

Weak Topics:
{weak_summary if weak_summary else "No significant weak topics identified yet."}

For each recommendation, provide:
1. A short title (max 50 chars)
2. A detailed description (2-3 sentences)
3. Subject (Physics/Chemistry/Maths/Biology/General)
4. Priority (High/Medium/Low)
5. Type (practice/revision/test)
6. Estimated time

Format as JSON array."""

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )

        import json
        content = response.choices[0].message.content
        # Try to parse JSON from the response
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        ai_recs = json.loads(content.strip())

        recommendations = []
        for rec in ai_recs:
            recommendations.append({
                "user_id": user_id,
                "title": rec.get("title", "Study recommendation"),
                "description": rec.get("description", ""),
                "subject": rec.get("subject", "General"),
                "priority": rec.get("priority", "Medium"),
                "type": rec.get("type", "practice"),
                "estimated_time": rec.get("estimated_time", "30 mins"),
            })

        return recommendations if recommendations else generate_recommendations(user_id, performance)

    except Exception:
        # Fallback to rule-based recommendations
        return generate_recommendations(user_id, performance)


def predict_score(performance: Dict, exam_type: str = "JEE Main") -> Dict:
    """
    Predict likely score range based on current performance trends.
    """
    overall_accuracy = performance.get("overall_accuracy", 0)
    subjects = performance.get("subjects", {})

    # JEE Main: 300 marks total (75 questions × 4 marks each)
    # NEET: 720 marks total (180 questions × 4 marks each)
    exam_configs = {
        "JEE Main": {"total_marks": 300, "total_questions": 75},
        "NEET": {"total_marks": 720, "total_questions": 180},
        "JEE Advanced": {"total_marks": 360, "total_questions": 54},
    }

    config = exam_configs.get(exam_type, exam_configs["JEE Main"])
    total_marks = config["total_marks"]

    # Base prediction from accuracy
    predicted_score = (overall_accuracy / 100) * total_marks

    # Adjust based on difficulty performance
    difficulty_factor = 1.0
    for subject, stats in subjects.items():
        hard_acc = stats.get("difficulty_breakdown", {}).get("Hard", {}).get("accuracy", 50)
        if hard_acc > 60:
            difficulty_factor += 0.05
        elif hard_acc < 30:
            difficulty_factor -= 0.05

    predicted_score *= difficulty_factor

    # Generate a range
    margin = total_marks * 0.1  # 10% margin
    low = max(0, round(predicted_score - margin))
    high = min(total_marks, round(predicted_score + margin))

    return {
        "exam_type": exam_type,
        "predicted_score": round(predicted_score),
        "score_range": {"low": low, "high": high},
        "total_marks": total_marks,
        "confidence": "medium" if performance.get("total_questions", 0) > 50 else "low",
        "overall_accuracy": overall_accuracy,
    }
