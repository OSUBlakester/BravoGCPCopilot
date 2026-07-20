// Interview Questions for AAC User Voice & Communication Profile
//
// GOAL: Collect just enough context so the LLM can generate communication options
// that (1) sound authentically like this person and (2) are factually accurate —
// e.g., not suggesting running for a wheelchair user or eating for a tube-fed user.
//
// Friends & family are captured in a separate interview (family-friends-interview-questions.js).
// The user_birthday question (id = 'user_birthday') is used by audio-interview-system.js
// to auto-populate the birthday field.

window.INTERVIEW_QUESTIONS = {

  // --- Who they are ---
  identity: [
    {
      id: 'user_name',
      question: 'What is the name of the person who will be using this app? Do they have any nicknames or preferred names that people use?',
      category: 'identity',
      required: false,
      followUp: 'How do family members and close friends usually address them?'
    },
    {
      id: 'user_birthday',
      question: 'When were they born? Please share their date of birth, including the year if you\'re comfortable.',
      category: 'identity',
      required: false,
      followUp: 'Is their birthday something they get excited about or enjoy celebrating?'
    }
  ],

  // --- Physical reality (critical for LLM accuracy) ---
  physical_reality: [
    {
      id: 'physical_reality',
      question: 'What physical or medical factors are important to know about them? For example: How do they get around — do they walk, use a wheelchair, or another device? Do they eat by mouth, or do they have a feeding tube or other dietary restrictions? Are there health conditions, physical limitations, or sensory needs the app should be aware of?',
      category: 'physical_reality',
      required: false,
      followUp: 'Are there any activities they are not able to do, or things they should not be offered as options, because of their physical situation?'
    },
    {
      id: 'living_situation',
      question: 'Where do they live and who do they live with? For example, do they live at home with family, in a group home, or another setting? Who are the main people they spend time with day to day?',
      category: 'physical_reality',
      required: false,
      followUp: 'Are there other people — caregivers, staff, siblings, or others — who are regularly part of their daily life?'
    }
  ],

  // --- Personality and communication voice ---
  personality: [
    {
      id: 'personality_traits',
      question: 'How would you describe their personality? Are they funny, serious, energetic, gentle, outgoing, or quiet? What makes them uniquely them?',
      category: 'personality',
      required: false,
      followUp: 'What personality trait do people notice or comment on most often?'
    },
    {
      id: 'communication_style',
      question: 'How do they naturally communicate — do they tend to be playful, direct, sweet, sarcastic, or expressive? How do they show happiness, excitement, or frustration?',
      category: 'personality',
      required: false,
      followUp: 'Do they have a signature style or way of expressing themselves that feels uniquely them?'
    }
  ],

  // --- What they love ---
  interests: [
    {
      id: 'favorite_activities',
      question: 'What are their favorite activities and games? What do they love to do most?',
      category: 'interests',
      required: false,
      followUp: 'What activity or game makes them most excited or that they ask for repeatedly?'
    },
    {
      id: 'favorite_items',
      question: 'What are their favorite items, toys, or clothes? Are there specific things they always want to have with them or wear?',
      category: 'interests',
      required: false,
      followUp: 'Do they have a special object, toy, or piece of clothing that means a lot to them?'
    },
    {
      id: 'entertainment_passions',
      question: 'What TV shows, movies, music, YouTube channels, books, or podcasts do they enjoy? Are there characters, songs, sports, athletes, sports teams, or specific topics they are really passionate about or talk about a lot?',
      category: 'interests',
      required: false,
      followUp: 'Are there any particular topics or things they could talk about endlessly?'
    },
    {
      id: 'food_drinks',
      question: 'What are their favorite foods, drinks, and restaurants? What do they love and what do they strongly dislike or refuse?',
      category: 'interests',
      required: false,
      followUp: 'Are there any foods, drinks, or restaurants they talk about, ask for, or get excited about regularly?'
    },
    {
      id: 'favorite_places',
      question: 'What are their favorite places to visit? What do they love to do when they are there?',
      category: 'interests',
      required: false,
      followUp: 'Are there places they ask to go often or get especially excited about visiting?'
    }
  ],

  // --- Communication needs and authentic voice ---
  communication: [
    {
      id: 'communication_style_needs',
      question: 'How do they typically express their wants and needs? Are they very direct and clear about what they want, or more subtle and indirect? Are they usually polite and patient, or do they tend to be more insistent?',
      category: 'communication',
      required: false,
      followUp: 'Can you give an example of how they might ask for something they really want?'
    },
    {
      id: 'assistance_needs',
      question: 'What kinds of help do they regularly need to ask for or communicate about? For example: repositioning, adjusting the room temperature, changing the TV, noise levels, comfort, or other physical needs that caregivers help with throughout the day.',
      category: 'communication',
      required: false,
      followUp: 'Are there specific requests they make often that can be hard to communicate quickly?'
    },
    {
      id: 'catch_phrases',
      question: 'Do they have favorite words, expressions, or phrases that are uniquely theirs — things they say often, their own spin on words, or expressions that really capture their personality?',
      category: 'communication',
      required: false,
      followUp: 'Are there any phrases or words that would make someone smile because they sound just like them?'
    },
    {
      id: 'communication_goals',
      question: 'What do they most want to be able to communicate? What messages or conversations matter most to them, and what topics get them most engaged or excited when talking with others?',
      category: 'communication',
      required: false,
      followUp: 'What would they most want to say if they could express anything to anyone?'
    }
  ],

  // --- Dislikes and avoidances ---
  dislikes: [
    {
      id: 'dislikes_avoidances',
      question: 'Are there activities, places, topics, or experiences they strongly dislike or want to avoid? For example, are there things that make them upset, anxious, or uncomfortable that the app should never suggest?',
      category: 'dislikes',
      required: false,
      followUp: 'Are there any words, phrases, or topics that are off-limits or that would be upsetting to see as a communication option?'
    }
  ],

  // --- Open-ended ---
  voice: [
    {
      id: 'anything_else',
      question: 'Is there anything else important about this person that would help the app generate options that truly sound like them and fit their life?',
      category: 'voice',
      required: false,
      followUp: 'What would you most want someone to know about them before they started helping them communicate?'
    }
  ]
};

// Configuration for the User Profile Interview
window.INTERVIEW_CONFIG = {
  minimumRequired: 7,
  questionsPerSession: 5,
  timeBetweenQuestions: 4000,
  maxAnswerLength: 2000,
  priorityCategories: ['identity', 'physical_reality', 'personality', 'communication', 'interests'],
  voiceCaptureAreas: {
    personality: ['personality_traits', 'communication_style'],
    preferences: ['food_drinks', 'favorite_items'],
    voiceElements: ['catch_phrases', 'communication_goals'],
    contextAreas: ['assistance_needs', 'favorite_places']
  }
};
