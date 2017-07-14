MISSING_PARAMS = u"I think you forgot some parameters :thinking_face:"
OK = u"OK :+1:"
PLEASE_SUBSCRIBE = u"If you want to participate in this survey, use the `join` command to subscribe"
# KL Changed: 'if' to 'If' in PLEASE_SUBSCRIBE
INVALID_TIME = u"Invalid time: `{}`"
# KL Changed: 'invalid' to 'Invalid' in INVALID_TIME
GREET_USER = u":wave: {} {} ! Let's talk in private :+1:"
# KL Changed: ':wink:' to ':+1:' in GREET_USER
INVITE_DM = ":point_right: slack://user?team={}&id={}"

#answers
ANSWERS_TOO_FEW = u"Hey...I think you forgot to enter some answers. I was expecting *{}* answers but only got *{}*."
ANSWERS_TOO_MANY = u"Whoa! You entered too many answers. I was expecting *{}* answers but you entered *{}*."
ANSWERS_INVALID = u"Invalid answer :thinking_face:"
# KL Changed 'invalid' to 'Invalid' in ANSWERS_INVALID
ANSWERS_BAD_CHOICE = u"Invalid choice for question *{}* :confused:"
# KL Changed 'invalid' to 'Invalid' in ANSWERS_BAD_CHOICE
ANSWERS_SAVE_OK = u"Answer saved :+1:"
# KL Changed answer to Answer in ANSWERS_SAVE_OK
ANSWERS_SAVE_FAIL = u"Error saving answer :cold_sweat:"
# KL Changed error to Error in ANSWERS_SAVE_FAIL
ANSWERS_CONFIRM = u"If you are happy with your responses, type `ok`, otherwise enter a new response. \nType `notes` to add a short note to this answer. \nYou can also `cancel` this answer. "
# KL Changed spelling of first 'responses', and changed 'hit' to 'type'
ANSWERS_DELETE_OK = u"All of your answers to survey _{}_ are gone :+1:"
# KL Changed to 'All of your' and added emoji.
ANSWERS_DELETE_FAIL = u"I could not delete your _{}_ survey answers :cold_sweat:"
ANSWERS_ADD_NOTE = u":writing_hand: Enter a short note about your survey response:"
# KL Changed from : ":writing_hand: enter a short note about your survey" to above text

#surveys
SURVEY_NOT_SUBSCRIBED = u"You are not subscribed to the _{0}_ survey yet :unamused: . To subscribe, type `@{1} join {0}`"
# KL Changed to above text from: "you are not subscribed to survey _{}_ :unamused:"
SURVEY_IS_SUBSCRIBED = u":hugging_face:  You already subscribed to the _{}_ survey"
# KL change to above text from: ":hugging_face: you aready subscribed survey _{}_ "
SURVEY_UNKNOWN = u"_{}_ survey does not exist :unamused:"
SURVEY_JOIN_OK = u"_{}_ survey subscribed :hugging_face:"
SURVEY_JOIN_FAIL = u"Could not subscribe to the _{}_ survey :cold_sweat:"
# KL Change: Added 'to'
SURVEY_LEAVE_OK = u"You left the _{}_ survey. \nI will keep your data and you can subscribe to this survey again anytime you want :relaxed: . \nUse the `delete` command if you want to wipe all of your answers"
# KL Change: Added 'to' after 'subscribe' and 'to' prior to 'want'
SURVEY_LEAVE_FAIL = u"Could not leave the _{}_ survey :cold_sweat:"
# KL Change: Capitalized 'C' in could
SURVEY_CANCELED = u"Survey canceled :neutral_face:"
# KL Change: Capitalized S in 'Survey'

#reminders
REMINDER_OK = u"I will remind you to take the _{}_ survey  at `{}`"
REMINDER_OK_2 = u"I will remind you to take the  _{}_  survey at `{}` and again at `{}`"
REMINDER_FAIL = u"Could not set a reminder for the _{}_ survey  :cold_sweat:"
# KL Change: Capitalized C in Could
REMINDER_REMOVE_OK = u"No more reminders for the _{}_ survey :v:"
REMIND_SURVEY = u"Psst! Don't forget to take the _{}_ survey ({}) :wink:"

#report
REPORT_FAIL = u"Could not retrieve answers for the _{}_ survey :cold_sweat:"
# KL Change: Capitalized C in Could
REPORT_EMPTY = u"You have no answers entered for the _{}_ survey"
# KL Changed wording above
NOTES_EMPTY = u"You have no notes saved with the _{}_ survey"
# KL Changed wording above
