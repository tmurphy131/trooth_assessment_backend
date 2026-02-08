#!/usr/bin/env python3
"""Test PDF generation with styled report"""

from app.services.master_trooth_report import render_pdf_v2

# Sample context with full premium report
context = {
    'apprentice_name': 'John Smith',
    'submitted_date': '2025-01-18T10:30:00Z',
    'overall_mc_percent': 75,
    'knowledge_band': 'Developing',
    'top_strengths': ['Prayer Life', 'Scripture Memory', 'Community Involvement'],
    'top_gaps': ['Bible Study Habits', 'Evangelism'],
    'categories': [
        {'name': 'Prayer', 'score': 8, 'level': 'Strong'},
        {'name': 'Scripture', 'score': 6, 'level': 'Growing'},
        {'name': 'Community', 'score': 7, 'level': 'Developing'},
    ],
    'knowledge_topics': [
        {'topic': 'Old Testament', 'percent': 80},
        {'topic': 'New Testament', 'percent': 65},
        {'topic': 'Church History', 'percent': 50},
    ],
    'open_insights': [
        {
            'category': 'Prayer Life', 
            'level': 'Mature', 
            'evidence': 'Shows deep prayer habits with consistent daily practice.',
            'mentor_moves': ['Encourage daily journaling', 'Introduce intercessory prayer']
        },
        {
            'category': 'Scripture Study',
            'level': 'Developing',
            'evidence': 'Reads Bible occasionally but lacks systematic approach.',
            'mentor_moves': ['Recommend Bible reading plan', 'Introduce SOAP method']
        }
    ],
    'starters': [
        'What has been your biggest spiritual challenge this week?', 
        'How can I pray for you?',
        'What Scripture has been speaking to you lately?'
    ],
    'four_week': {
        'rhythm': ['Daily devotions', 'Weekly check-in', 'Monthly review'], 
        'checkpoints': ['Week 2: Review progress', 'Week 4: Set new goals']
    },
    'priority_action': {
        'title': 'Start Daily Scripture Reading',
        'description': 'Begin each day with 15 minutes of focused Bible reading',
        'scripture': 'Psalm 119:105 - Your word is a lamp to my feet'
    },
    'resources': [
        {'title': 'Spiritual Disciplines Handbook', 'type': 'Book', 'why': 'Comprehensive guide for beginners'},
        {'title': 'Bible Project', 'type': 'Video', 'why': 'Visual overview of Scripture'}
    ],
    'full_report': {
        'executive_summary': {
            'one_liner': 'John shows strong foundations with room for growth in outreach.',
            'trajectory_note': 'Trending positively over the past month with increased prayer consistency.'
        },
        'strengths_deep_dive': [
            {
                'area': 'Prayer Life', 
                'summary': 'John demonstrates consistent daily prayer with a heart for intercession.', 
                'how_to_leverage': 'Consider leading a prayer group or mentoring others in prayer.'
            },
            {
                'area': 'Community Involvement',
                'summary': 'Active participant in small group and Sunday worship.',
                'how_to_leverage': 'Could take on a serving role or help welcome newcomers.'
            }
        ],
        'gaps_deep_dive': [
            {
                'area': 'Evangelism', 
                'summary': 'Hesitant to share faith with others, lacks confidence in articulating beliefs.', 
                'biblical_perspective': 'Matthew 28:19-20 - The Great Commission calls us to make disciples.',
                'growth_pathway': {
                    'phase_1_weeks_1_4': {
                        'goal': 'Share testimony with one friend this month'
                    }
                }
            },
            {
                'area': 'Bible Study',
                'summary': 'Scripture engagement is sporadic and surface-level.',
                'biblical_perspective': '2 Timothy 2:15 - Be diligent to present yourself approved.',
                'growth_pathway': {
                    'phase_1_weeks_1_4': {
                        'goal': 'Complete one book study using the SOAP method'
                    }
                }
            }
        ],
        'conversation_guide': {
            'opening_questions': [
                'What has God been teaching you lately?', 
                'Where do you feel stuck in your spiritual growth?',
                'What brings you the most joy in your walk with Christ?'
            ],
            'sessions': [
                {'focus': 'Prayer Life', 'goal': 'Explore deeper prayer practices and spiritual disciplines'},
                {'focus': 'Scripture Study', 'goal': 'Establish consistent Bible reading habits'},
                {'focus': 'Evangelism', 'goal': 'Build confidence in sharing faith naturally'}
            ]
        }
    }
}

pdf = render_pdf_v2(context)
print(f'PDF generated: {len(pdf)} bytes')

# Save for inspection
with open('/tmp/test_report.pdf', 'wb') as f:
    f.write(pdf)
print('Saved to /tmp/test_report.pdf')
print('Open with: open /tmp/test_report.pdf')
