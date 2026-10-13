"""Per-gift guidance shown in the Spiritual Gifts PDF (specs/008-pdf-redesign, FR-011/FR-012).

Keyed by the gift slugs in ``app.core.spiritual_gifts_map.MAP``. Scripture is given as
references only (no quoted verse text). Wording is pending product-owner review.

Each entry:
    scriptures:    2-3 references
    ways_to_serve: >= 3 short imperative sentences (<= 120 chars each)
    reflection:    one question
"""
from __future__ import annotations

GIFT_GUIDANCE: dict[str, dict] = {
    "leadership": {
        "scriptures": ["Romans 12:8", "Nehemiah 2:17-18", "Hebrews 13:7"],
        "ways_to_serve": [
            "Lead a small group, team or project that needs clear direction.",
            "Help a ministry set goals and keep people moving toward them.",
            "Invest in a younger leader by sharing responsibility with them.",
        ],
        "reflection": "Where are people already looking to you for direction, and how can you lead them toward Christ?",
    },
    "pastor-shepherd": {
        "scriptures": ["Ephesians 4:11-12", "1 Peter 5:2-3", "John 10:11"],
        "ways_to_serve": [
            "Check in regularly on a few people and walk with them through life.",
            "Lead or co-lead a small group focused on care and growth.",
            "Follow up with newcomers and help them find community.",
        ],
        "reflection": "Who has God placed in your care right now, and how are you shepherding them?",
    },
    "discernment": {
        "scriptures": ["1 Corinthians 12:10", "1 John 4:1", "Hebrews 5:14"],
        "ways_to_serve": [
            "Pray with leaders before major decisions and share what you sense.",
            "Help others test teaching and ideas against Scripture.",
            "Serve on a team that evaluates new ministries or partnerships.",
        ],
        "reflection": "How do you test your impressions against Scripture before you share them?",
    },
    "exhortation": {
        "scriptures": ["Romans 12:8", "Hebrews 3:13", "1 Thessalonians 5:11"],
        "ways_to_serve": [
            "Write notes or send messages that encourage people in their faith.",
            "Come alongside someone who is discouraged and help them take a next step.",
            "Mentor or coach someone toward a specific area of growth.",
        ],
        "reflection": "Who needs encouragement from you this week, and what will you say?",
    },
    "hospitality": {
        "scriptures": ["1 Peter 4:9", "Romans 12:13", "Hebrews 13:2"],
        "ways_to_serve": [
            "Host a meal, Bible study or small group in your home.",
            "Greet and welcome guests at church gatherings.",
            "Make a point to include people who are new or on the edges.",
        ],
        "reflection": "Who could you invite in this month who rarely gets invited?",
    },
    "prophecy": {
        "scriptures": ["1 Corinthians 14:3", "Romans 12:6", "1 Thessalonians 5:20-21"],
        "ways_to_serve": [
            "Speak biblical truth with love when your community needs clarity.",
            "Pray for others and share Scripture that builds them up.",
            "Invite mature believers to weigh and confirm what you share.",
        ],
        "reflection": "Does what you speak strengthen, encourage and comfort others?",
    },
    "knowledge": {
        "scriptures": ["1 Corinthians 12:8", "Colossians 2:2-3", "Proverbs 2:6"],
        "ways_to_serve": [
            "Research and prepare study material for teachers or groups.",
            "Help others understand the background and context of Scripture.",
            "Answer questions about the faith with patience and care.",
        ],
        "reflection": "How are you turning what you know into love and service for others?",
    },
    "miracles": {
        "scriptures": ["1 Corinthians 12:10", "Acts 19:11-12", "Mark 16:17-18"],
        "ways_to_serve": [
            "Join or lead a prayer team that prays boldly for God to act.",
            "Pray with people in crisis, trusting God for the outcome.",
            "Share stories of God's work in ways that point to Him, not you.",
        ],
        "reflection": "When God works through you, how do you keep the glory pointed to Him?",
    },
    "healing": {
        "scriptures": ["1 Corinthians 12:9", "James 5:14-16", "Acts 3:6-8"],
        "ways_to_serve": [
            "Pray for the sick at church, in hospitals or at home.",
            "Serve on a care or prayer ministry for people who are hurting.",
            "Walk patiently with people whose healing is slow or unseen.",
        ],
        "reflection": "How do you care for someone when healing does not come the way you hoped?",
    },
    "helps": {
        "scriptures": ["1 Corinthians 12:28", "Romans 16:1-2", "Acts 6:2-4"],
        "ways_to_serve": [
            "Take on behind-the-scenes tasks that free leaders to focus.",
            "Serve on a setup, tech, kitchen or facilities team.",
            "Ask a leader you respect what would lighten their load this month.",
        ],
        "reflection": "Whose work could you make easier this week without needing to be noticed?",
    },
    "mercy": {
        "scriptures": ["Romans 12:8", "Luke 10:33-37", "Matthew 25:35-36"],
        "ways_to_serve": [
            "Visit people who are sick, grieving, elderly or isolated.",
            "Serve with a ministry to the poor, homeless or hurting.",
            "Sit with someone in pain and listen before you try to fix.",
        ],
        "reflection": "Who in your life is hurting, and what would compassion look like for them right now?",
    },
    "evangelism": {
        "scriptures": ["Ephesians 4:11", "Acts 8:26-35", "2 Timothy 4:5"],
        "ways_to_serve": [
            "Pray for and build friendships with people who don't know Jesus.",
            "Practice sharing your testimony and the gospel in two minutes.",
            "Help with outreach events or train others to share their faith.",
        ],
        "reflection": "Which three people are you praying will come to know Jesus?",
    },
    "faith": {
        "scriptures": ["1 Corinthians 12:9", "Hebrews 11:1, 6", "Mark 11:22-24"],
        "ways_to_serve": [
            "Pray with confidence over your church's vision and needs.",
            "Encourage others to trust God when circumstances look impossible.",
            "Step into a new ministry that needs someone willing to trust God first.",
        ],
        "reflection": "What is God asking you to trust Him for that only He can do?",
    },
    "teaching": {
        "scriptures": ["Romans 12:7", "James 3:1", "2 Timothy 2:2"],
        "ways_to_serve": [
            "Teach a class, Bible study or youth or children's group.",
            "Explain a passage clearly and help others apply it to daily life.",
            "Train and equip the next group of teachers.",
        ],
        "reflection": "How are you living what you teach, so others can follow your example?",
    },
    "wisdom": {
        "scriptures": ["1 Corinthians 12:8", "James 1:5", "James 3:17"],
        "ways_to_serve": [
            "Make yourself available to people facing hard decisions.",
            "Serve on a counsel, elder or advisory team.",
            "Help others apply Scripture to real situations they are facing.",
        ],
        "reflection": "Who is asking for your counsel, and how are you pointing them to Scripture?",
    },
    "intercession": {
        "scriptures": ["Colossians 4:12", "1 Timothy 2:1-2", "Ephesians 6:18"],
        "ways_to_serve": [
            "Keep a prayer list and pray for it faithfully every day.",
            "Join or lead a prayer team for your church, leaders or city.",
            "Ask people how you can pray, then follow up with them.",
        ],
        "reflection": "Who or what is God putting on your heart to pray for consistently?",
    },
    "service": {
        "scriptures": ["Romans 12:7", "1 Peter 4:10-11", "Galatians 5:13"],
        "ways_to_serve": [
            "Meet a practical need for a family or neighbor this week.",
            "Commit to a regular serving team and show up reliably.",
            "Notice what needs doing and do it before you are asked.",
        ],
        "reflection": "How can your everyday acts of service point people to Jesus?",
    },
    "tongues-interpretation": {
        "scriptures": ["1 Corinthians 12:10", "1 Corinthians 14:13, 26-28", "Acts 2:4"],
        "ways_to_serve": [
            "Use this gift in personal prayer to grow in intimacy with God.",
            "In gatherings, follow Scripture's order so the church is built up.",
            "Ask mature leaders to help you use this gift with wisdom.",
        ],
        "reflection": "How does your use of this gift build up the church, not only yourself?",
    },
    "giving": {
        "scriptures": ["Romans 12:8", "2 Corinthians 9:6-8", "Acts 4:34-37"],
        "ways_to_serve": [
            "Give generously and regularly to your church and gospel work.",
            "Quietly meet a specific financial need you become aware of.",
            "Help others grow in stewardship, budgeting and generosity.",
        ],
        "reflection": "Where is God inviting you to give with more joy and less hesitation?",
    },
    "missionary": {
        "scriptures": ["Acts 13:2-3", "Romans 10:14-15", "1 Corinthians 9:22-23"],
        "ways_to_serve": [
            "Build friendships across cultures in your own community.",
            "Join a short-term mission trip or support those who go.",
            "Learn about an unreached people group and pray for them.",
        ],
        "reflection": "What people or place is God stirring your heart toward?",
    },
    "apostleship": {
        "scriptures": ["Ephesians 4:11-12", "1 Corinthians 12:28", "Romans 15:20"],
        "ways_to_serve": [
            "Help launch a new ministry, group or church plant.",
            "Build systems and leaders so new work can last and multiply.",
            "Bring the gospel into places where the church isn't yet present.",
        ],
        "reflection": "What new work might God want to start through you, and who could you build it with?",
    },
    "craftsmanship": {
        "scriptures": ["Exodus 31:1-5", "Exodus 35:30-35", "Colossians 3:23"],
        "ways_to_serve": [
            "Build, repair or design things your church or ministry needs.",
            "Use your craft to bless a family in need.",
            "Teach your skill to others as a way to build relationships.",
        ],
        "reflection": "How can the work of your hands become an act of worship?",
    },
    "administration": {
        "scriptures": ["1 Corinthians 12:28", "Luke 14:28-30", "Titus 1:5"],
        "ways_to_serve": [
            "Organize an event, schedule or process for a ministry team.",
            "Help a leader turn a vision into a clear plan with next steps.",
            "Create systems that help volunteers know what to do and when.",
        ],
        "reflection": "Which ministry would flourish if someone brought order to it, and could that be you?",
    },
    "music-worship": {
        "scriptures": ["1 Chronicles 25:1-7", "Psalm 96:1-3", "Colossians 3:16"],
        "ways_to_serve": [
            "Join a worship team as a singer, musician or technician.",
            "Lead worship for a small group, youth or children's ministry.",
            "Write or arrange songs that help others remember God's truth.",
        ],
        "reflection": "How do you keep worship focused on God rather than on performance?",
    },
}
