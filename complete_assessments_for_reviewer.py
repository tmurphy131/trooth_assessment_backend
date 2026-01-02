"""
Script to complete assessments for the Apple reviewer apprentice account.
Run each assessment one at a time with specified accuracy levels.
"""
import os
import sys
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.user import User
from app.models.assessment_template import AssessmentTemplate
from app.models.assessment_template_question import AssessmentTemplateQuestion
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.assessment_draft import AssessmentDraft
from app.models.assessment import Assessment

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    print("Set it with: export DATABASE_URL='postgresql://...'")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

def get_apprentice():
    """Get the Apple reviewer apprentice account."""
    user = db.query(User).filter(User.email == 'apple.reviewer.apprentice@onlyblv.com').first()
    if not user:
        print("ERROR: Apple reviewer apprentice account not found!")
        print("Make sure the account exists with email: apple.reviewer.apprentice@onlyblv.com")
        sys.exit(1)
    print(f"Found apprentice: {user.name} ({user.email}), ID: {user.id}")
    return user

def get_template_by_key(key_pattern: str):
    """Get an assessment template by key pattern."""
    template = db.query(AssessmentTemplate).filter(
        AssessmentTemplate.key.ilike(f'%{key_pattern}%'),
        AssessmentTemplate.published == True
    ).first()
    if not template:
        print(f"ERROR: No published template found matching '{key_pattern}'")
        sys.exit(1)
    print(f"Found template: {template.name} (key: {template.key}), ID: {template.id}")
    return template

def get_template_questions(template_id: str):
    """Get all questions for a template with their options."""
    # Get template question associations
    tq_assocs = db.query(AssessmentTemplateQuestion).filter(
        AssessmentTemplateQuestion.template_id == template_id
    ).order_by(AssessmentTemplateQuestion.order).all()
    
    questions = []
    for tq in tq_assocs:
        question = db.query(Question).filter(Question.id == tq.question_id).first()
        if question:
            options = db.query(QuestionOption).filter(
                QuestionOption.question_id == question.id
            ).order_by(QuestionOption.order).all()
            questions.append({
                'id': question.id,
                'code': question.question_code,
                'text': question.text,
                'type': question.question_type,
                'options': [{'id': o.id, 'text': o.option_text, 'is_correct': o.is_correct} for o in options]
            })
    
    print(f"Found {len(questions)} questions for template")
    return questions

def generate_answers(questions: list, target_accuracy: float):
    """Generate answers with approximately the target accuracy for MC questions."""
    answers = {}
    mc_questions = [q for q in questions if q['type'] == 'multiple_choice' and q['options']]
    open_questions = [q for q in questions if q['type'] == 'open_ended']
    
    # Calculate how many MC questions to get correct
    num_correct = int(len(mc_questions) * target_accuracy)
    
    # Randomly select which questions to answer correctly
    correct_indices = set(random.sample(range(len(mc_questions)), num_correct))
    
    print(f"\nMC Questions: {len(mc_questions)}, targeting {num_correct} correct ({target_accuracy*100:.0f}%)")
    print(f"Open-ended Questions: {len(open_questions)}")
    
    # Generate MC answers
    for i, q in enumerate(mc_questions):
        correct_option = next((o for o in q['options'] if o['is_correct']), None)
        incorrect_options = [o for o in q['options'] if not o['is_correct']]
        
        if i in correct_indices and correct_option:
            # Answer correctly
            answers[q['code']] = correct_option['text']
        elif incorrect_options:
            # Answer incorrectly
            answers[q['code']] = random.choice(incorrect_options)['text']
        elif correct_option:
            # No incorrect options, have to answer correctly
            answers[q['code']] = correct_option['text']
    
    # Generate open-ended answers (these get AI scored, give reasonable answers)
    open_answer_templates = [
        "I believe this relates to God's love and grace for humanity.",
        "This teaches us about faith, obedience, and trusting in God's plan.",
        "The key principle here is to follow Christ's example in our daily lives.",
        "This passage shows us the importance of prayer and spiritual discipline.",
        "I think this means we should love others as God loves us.",
        "This reminds me of the importance of community and fellowship.",
        "The lesson here is about perseverance and staying faithful.",
        "This speaks to God's sovereignty and our role in His kingdom.",
        "I see this as a call to be more intentional about my spiritual growth.",
        "This challenges me to examine my heart and motives.",
    ]
    
    for i, q in enumerate(open_questions):
        # Use a template answer with some variation
        base_answer = open_answer_templates[i % len(open_answer_templates)]
        answers[q['code']] = f"{base_answer} Reflecting on {q['text'][:50]}..."
    
    return answers

def complete_assessment(user_id: str, template_id: str, answers: dict, template_name: str):
    """Create and submit an assessment draft."""
    from datetime import datetime
    import uuid
    
    # Check for existing draft
    existing_draft = db.query(AssessmentDraft).filter(
        AssessmentDraft.user_id == user_id,
        AssessmentDraft.template_id == template_id,
        AssessmentDraft.is_submitted == False
    ).first()
    
    if existing_draft:
        print(f"Found existing draft, updating it...")
        draft = existing_draft
        draft.answers = answers
        draft.updated_at = datetime.utcnow()
    else:
        print(f"Creating new draft...")
        draft = AssessmentDraft(
            id=str(uuid.uuid4()),
            user_id=user_id,
            template_id=template_id,
            answers=answers,
            is_submitted=False
        )
        db.add(draft)
    
    db.commit()
    print(f"Draft saved with {len(answers)} answers")
    
    # Now submit the draft
    print(f"Submitting draft...")
    draft.is_submitted = True
    draft.submitted_at = datetime.utcnow()
    db.commit()
    
    print(f"\n✅ Assessment '{template_name}' submitted successfully!")
    print(f"   Draft ID: {draft.id}")
    print(f"   Note: AI scoring will happen when the backend processes this submission.")
    
    return draft

def main():
    print("=" * 60)
    print("Assessment Completion Script for Apple Reviewer Account")
    print("=" * 60)
    
    # Assessment configurations
    assessments = [
        ("master_trooth", 0.70, "Master Trooth Assessment"),
        ("genesis", 0.80, "Genesis Assessment"),
        ("matthew", 0.50, "Matthew Assessment"),  
        ("gospel_fluency", 0.78, "Gospel Fluency Assessment"),
    ]
    
    print("\nWhich assessment do you want to complete?")
    for i, (key, accuracy, name) in enumerate(assessments, 1):
        print(f"  {i}. {name} ({accuracy*100:.0f}% accuracy)")
    print("  0. Exit")
    
    choice = input("\nEnter number: ").strip()
    
    if choice == "0":
        print("Exiting...")
        return
    
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(assessments):
            print("Invalid choice")
            return
    except ValueError:
        print("Invalid input")
        return
    
    key, accuracy, name = assessments[idx]
    
    print(f"\n--- Completing {name} at {accuracy*100:.0f}% accuracy ---\n")
    
    # Get apprentice
    apprentice = get_apprentice()
    
    # Get template
    template = get_template_by_key(key)
    
    # Get questions
    questions = get_template_questions(template.id)
    
    if not questions:
        print("ERROR: No questions found for template")
        return
    
    # Generate answers
    answers = generate_answers(questions, accuracy)
    
    # Complete the assessment
    complete_assessment(apprentice.id, template.id, answers, name)
    
    print("\n" + "=" * 60)
    print("Done! Run the script again for the next assessment.")
    print("=" * 60)

if __name__ == "__main__":
    main()
