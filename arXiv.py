import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    ChatAction,
    LabeledPrice
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    PreCheckoutQueryHandler
)
from arxiv_categories import ARXIV_CATEGORIES
from advanced_search_handlers import (
    show_advanced_search_menu,
    handle_filter_selection,
    handle_date_input,
    handle_author_input,
    handle_citations_input,
    handle_filter_execute,
    handle_custom_date_message,
    handle_main_category_selection,
    handle_subcategory_selection,
    handle_category_toggle,
    cancel_search,
    CHOOSING_FILTER,
    ENTER_DATE_FROM,
    ENTER_DATE_TO,
    ENTER_AUTHOR,
    ENTER_MIN_CITATIONS,
    SAVE_FILTER
)
from chat_handler import ChatHandler
from document_handler import DocumentHandler
import telegram
from typing import Dict, List, Optional
from telegram.error import TimedOut, NetworkError, BadRequest
import paper_comparison
from voice_handler import VoiceSearchHandler
from user_preferences import UserPreferences
from notifications import NotificationPreferences
import arxiv
import google.generativeai as genai
import os
from datetime import datetime, timedelta
import requests
from io import BytesIO
from dotenv import load_dotenv
import time
import random
import json
from admin_handler import AdminManager
import asyncio

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configure Gemini AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("❌ Google API Key not found in environment variables!")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# Get Telegram token from environment variables
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ Telegram token not found in environment variables!")

MAX_PAPERS_TO_COMPARE = 3
MAX_RESPONSE_LENGTH = 4096  # Telegram's message length limit
RATE_LIMIT_DELAY = 1  # seconds between messages

# Channel config
CHANNEL_USERNAME = "@TheodoreI1"  # For display purposes
CHANNEL_ID = -1002412839333

# Fun messages for non-subscribers
JOIN_MESSAGES = [
    "🚫 Hold up! VIP access required - join our channel first! 😎",
    "🔒 Exclusive content alert! Channel members only! 🎭",
    "🎯 Almost there! One click to unlock infinite knowledge! 🧠",
    "🎪 Welcome to the future of research! (Channel members only) 🚀",
    "💫 Want to see something cool? Join our channel first! ✨",
    "🌟 Plot twist: The real magic happens in our channel! 🪄",
    "🎭 Sorry, this is a members-only party! Ready to join? 🎉",
]

join_messages = """
🌟 *Welcome to PaperPilot, the Future of Research!* 🌟

Hey there, future innovator! 👋 You're just one step away from unlocking a world of cutting-edge research, AI-powered insights, and exclusive content. By joining our channel, you'll gain access to:

🚀 *Exclusive Research Papers* - Get the latest and most relevant papers delivered straight to you.
🤖 *AI-Powered Summaries* - Understand complex research in seconds with our smart summaries.
🔬 *Interactive Q&A* - Ask questions and get detailed answers based on the latest research.
📥 *Direct PDF Downloads* - Download papers instantly and keep them for offline reading.
🎯 *Smart Navigation* - Easily browse through papers and find exactly what you need.

Join our channel now and become part of a community that's shaping the future of knowledge. Don't miss out on this opportunity to elevate your research game! 🌍

Let's explore the universe of knowledge together! 🚀
"""

WELCOME_MESSAGE = """
🎓 *Welcome to PaperPilot - Research Assistant!*

Your AI-powered research companion! Let's explore the world of science together! 🚀

*Features:*
📚 Smart Paper Search
🤖 AI-Powered Summaries
❓ Interactive Q&A
📥 Direct PDF Downloads
🎯 Paper-by-Paper Navigation

*Commands:*
/search `<query>` - Search for papers
/help - Show help message
/latest - Get latest papers
/about - About this bot
"""

HELP_MESSAGE = """
*How to use PaperPilot - Research Assistant* 📚

1. *Search for papers:*
   `/search machine learning`

2. *Get AI summary:*
   Click the '🤖 Summarize' button on any paper

3. *Ask questions:*
   After getting a summary, just type your question!

4. *Navigate results:*
   Use '➡️ More Results' to explore papers

🎙️ *Voice Search Features:*
• Send a voice message with your search query
• Edit transcribed text if needed
• Retry if transcription isn't perfect
• Quick search with one tap
• Works in multiple languages!

*Pro Tips:*
🎯 Speak clearly and at a moderate pace
🌟 Use specific keywords in your voice query
🔊 Avoid background noise for better results

*Pro Tips:*
• Add year for recent papers
• Use specific keywords
• Try different search terms
• Ask follow-up questions

Need more help? Feel free to ask! 🤖
"""

ABOUT_MESSAGE = f"""
**✨ Yo, what’s good? I’m PaperPilot!**
Your AI-powered research dude, created by [Theodore](https://t.me/FirafisBekele) —a high school dev with cosmic ambitions. Let’s break it down:

---

**🎯 *Why I Exist***
Inspired by *Dagmawi Babi*’s 🔥 [ScholarXiv](https://play.google.com/store/apps/details?id=com.scholarxiv.app) app, Theodore thought:
*"Let’s make research papers* ***easy*** *to explore!"*
So here I am—smarter, faster, and always down to:
• 🤖 **Summarize** dense papers in plain English
• 🔍 **Connect** concepts across studies
• 🚀 **Guide** you through the knowledge universe

---

**⚡ *Current Struggle***
Right now, I’m running on *free-tier hosting*:
• 🌙 **Downtimes happen** (I hate naps!)
• 🐢 **Speed limits** (my brain’s *too* powerful for this)
• 💸 **Funded by Theodore’s ramen budget** ( you know, high school life!)

{random.choice([
    "🌟 *Fun fact:* $10 = 100 extra papers I can process daily!",
    "🚀 *Pro tip:* Paid hosting = instant 24/7 access for everyone!",
])}

---

**🙌 *How You Can Help***
• ☕ **Donate** (even 1 cent keeps me alive!)
• 📢 **Share me** with researchers/students
• 💡 **Suggest features** to level me up

*"Let’s turn PDFs into pure knowledge fuel!"* 🔥
"""

class UserSession:
    def __init__(self):
        self.papers_to_compare = []
        self.last_activity = datetime.utcnow()
        self.comparison_count = 0
        self.daily_limit = 10

    def can_compare(self) -> bool:
        """Check if user hasn't exceeded daily comparison limit."""
        if (datetime.utcnow() - self.last_activity).days >= 1:
            self.comparison_count = 0
        return self.comparison_count < self.daily_limit

    def record_comparison(self):
        """Record a comparison activity."""
        self.comparison_count += 1
        self.last_activity = datetime.utcnow()

def check_channel_subscription(update: Update, context: CallbackContext) -> bool:
    """Check if the user is subscribed to the channel."""
    try:
        user_id = update.effective_user.id
        chat_member = context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

        if chat_member.status in ['member', 'administrator', 'creator']:
            return True

        keyboard = [[InlineKeyboardButton("🌟 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        join_message = join_messages

        update.effective_message.reply_text(
            f"{join_message}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return False

    except Exception as e:
        logger.error(f"❌ Channel subscription check error: {e}")

        # Handle "Chat not found" issue specifically
        if "Chat not found" in str(e):
            update.effective_message.reply_text("🚨 Error: The bot cannot access the channel. Make sure it is an admin!")

        return False

def subscription_required(func):
    """Decorator to check channel subscription."""
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if check_channel_subscription(update, context):
            return func(update, context, *args, **kwargs)
    return wrapper

def generate_paper_summary(paper):
    """Generate summary using Gemini."""
    prompt = f"""
    Please provide a clear and engaging summary of this research paper:

    Title: {paper.title}
    Authors: {', '.join(str(author) for author in paper.authors)}

    Abstract:
    {paper.summary}

    Please cover:
    1. Main research objective
    2. Key methodology
    3. Important findings
    4. Real-world impact
    5. Key innovations

    Make it informative yet accessible for a general audience.
    """

    response = model.generate_content(prompt)
    return response.text

def format_paper(paper) -> str:
    """Format paper details with emojis and markdown."""
    authors = [str(author) for author in paper.authors[:3]]
    authors_text = ', '.join(authors)

    safe_title = paper.title.replace('*', r'\*').replace('_', r'\_').replace('[', r'\[').replace(']', r'\]')
    safe_category = paper.primary_category.replace('*', r'\*').replace('_', r'\_')
    safe_summary = paper.summary[:300].replace('*', r'\*').replace('_', r'\_')

    keyboard = [
        [
            InlineKeyboardButton("📚 Read Paper", url=f"https://arxiv.org/abs/{paper.get_short_id()}"),
            InlineKeyboardButton("🤖 Summarize", callback_data=f"summarize_{paper.get_short_id()}")
        ],
        [
            InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{paper.get_short_id()}"),
            InlineKeyboardButton("➕ Add to Compare", callback_data=f"compare_add_{paper.get_short_id()}")
        ]
    ]

    return f"""
📄 *Title:* {safe_title}
👥 *Authors:* {authors_text} {'...' if len(paper.authors) > 3 else ''}
📅 *Published:* {paper.published.strftime('%Y-%m-%d')}
🏷️ *Categories:* {safe_category}

📝 *Abstract:*
{safe_summary}...

🔗 [Read Full Paper]({paper.pdf_url})
"""

@subscription_required
def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message when /start is issued."""
    update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN
    )

@subscription_required
def help_command(update: Update, context: CallbackContext) -> None:
    """Send help message when /help is issued."""
    update.message.reply_text(
        HELP_MESSAGE,
        parse_mode=ParseMode.MARKDOWN
    )

@subscription_required
def about_command(update: Update, context: CallbackContext) -> None:
    """Show information about the bot."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Support PaperPilot",callback_data="show_support_options")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        ABOUT_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

def handle_support_options(update: Update, context: CallbackContext) -> None:
    """Handle support button clicks and show payment options."""
    query = update.callback_query
    query.answer()

    if query.data == "show_support_options":
        thank_you_message = """
✨ *A Heartfelt Thank You!* ✨

Your consideration to support PaperPilot means the world to me! It's amazing to see people who believe in making research accessible to everyone. Your support will help keep this bot running 24/7 and enable us to add even more exciting features!

Choose your preferred way to help:
"""
        keyboard = [
            [InlineKeyboardButton(
                "⭐️ Stars - Support via Telegram",
                callback_data="stars_donation"
            )],
            [InlineKeyboardButton(
                "☕️ Buy Me a Coffee",
                url="https://www.buymeacoffee.com/theodore_dev"
            )],
            [InlineKeyboardButton(
                "📱 Telebirr",
                callback_data="show_telebirr_info"
            )],
            [InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_to_about"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.message.edit_text(
            thank_you_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    elif query.data == "stars_donation":
        stars_message = """
🌟 *Support PaperPilot with Telegram Stars* 🌟

Ready to help keep PaperPilot flying high? Click below to choose your donation amount!

Your support fuels 24/7 research awesomeness! 🚀
"""
        keyboard = [
            [InlineKeyboardButton(
                "💸 Donate with Stars",
                callback_data="start_stars_donation"
            )],
            [InlineKeyboardButton(
                "🔙 Back to Options",
                callback_data="show_support_options"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.message.edit_text(
            stars_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    elif query.data == "show_telebirr_info":
        telebirr_message = """
📱 *Telebirr Payment Details*

You can support PaperPilot directly through Telebirr:

👤 *Account Name:* Theodore
📱 *Phone:* +251912345678
💫 *Message:* PaperPilot Support

_Thank you for helping keep the research flowing!_ ✨
"""
        keyboard = [[InlineKeyboardButton("🔙 Back to Options", callback_data="show_support_options")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.message.edit_text(
            telebirr_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    elif query.data == "back_to_about":
        about_command(update, context)

def start_stars_donation(update: Update, context: CallbackContext) -> None:
    """Prompt user to enter the number of Stars to donate."""
    query = update.callback_query
    query.answer()

    context.user_data['awaiting_stars_amount'] = True

    prompt_message = """
🌟 *How Many Stars?* 🌟

Please send a number to tell me how many Stars you'd like to donate to PaperPilot (e.g., 10, 50, 100).

*Note:* Minimum is 1 Star. Let's keep the research flowing! 🚀
"""
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="show_support_options")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.message.edit_text(
        prompt_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

def handle_stars_amount(update: Update, context: CallbackContext) -> None:
    """Handle user input for Stars donation amount."""
    if not context.user_data.get('awaiting_stars_amount'):
        return

    user_input = update.message.text.strip()
    try:
        amount = int(user_input)
        if amount < 1:
            update.message.reply_text(
                "❌ Please enter a number of Stars greater than 0! Try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    except ValueError:
        update.message.reply_text(
            "❌ That’s not a valid number! Please send a number like 10, 50, or 100.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    context.user_data['awaiting_stars_amount'] = False
    context.user_data['stars_donation_amount'] = amount

    confirm_message = f"""
🌟 *Awesome Choice!* 🌟

You’re about to donate *{amount} Stars* to PaperPilot. This will help keep the bot running 24/7! 🚀

Click below to confirm and proceed with payment.
"""
    keyboard = [
        [InlineKeyboardButton(
            "💳 Confirm Donation",
            callback_data=f"confirm_stars_{amount}"
        )],
        [InlineKeyboardButton(
            "🔙 Change Amount",
            callback_data="start_stars_donation"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        confirm_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

def confirm_stars_donation(update: Update, context: CallbackContext) -> None:
    """Create a Telegram Stars invoice for the donation."""
    query = update.callback_query
    query.answer()

    try:
        amount = int(query.data.split('_')[-1])
        user = update.effective_user

        # Create invoice payload with unique identifier
        payload = f"donation_{user.id}_{int(time.time())}"

        # Create labeled price (amount in cents)
        prices = [LabeledPrice(f"PaperPilot Donation ({amount} Stars)", amount * 100)]

        # Send invoice
        context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title="PaperPilot Donation",
            description=f"Thank you for donating {amount} Stars to support PaperPilot!",
            payload=payload,
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",     # Currency code for Telegram Stars
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )

    except Exception as e:
        logger.error(f"Failed to create invoice: {e}")
        query.message.reply_text(
            "❌ Failed to create payment. Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )


"""
        keyboard = [
            [InlineKeyboardButton("💸 Pay Now", url=invoice_link)],
            [InlineKeyboardButton("🔙 Back to Options", callback_data="show_support_options")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.message.edit_text(
            payment_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
"""


def pre_checkout_query(update: Update, context: CallbackContext) -> None:
    """Handle pre-checkout query for Stars payments."""
    query = update.pre_checkout_query
    try:
        # Validate the payload format
        if query.invoice_payload.startswith("donation_"):
            query.answer(ok=True)
        else:
            query.answer(ok=False, error_message="Invalid payment request")
    except Exception as e:
        logger.error(f"Pre-checkout error: {e}")
        query.answer(ok=False, error_message="Payment processing error")

def successful_payment(update: Update, context: CallbackContext) -> None:
    """Handle successful Stars payment."""
    payment = update.message.successful_payment
    user = update.effective_user
    stars = payment.total_amount // 100  # Convert from cents

    logger.info(f"User {user.id} donated {stars} Stars")

    update.message.reply_text(
        f"""
🌟 *Thank You for Your Support!* 🌟

You've successfully donated *{stars} Stars* to PaperPilot!

Your contribution helps keep the bot running and supports future improvements.

We appreciate your generosity! 🚀
        """,
        parse_mode=ParseMode.MARKDOWN
    )

    # Clear any donation-related user data
    context.user_data.pop('stars_donation_amount', None)

def add_support_handlers(dispatcher):
    """Add support-related handlers to the dispatcher."""
    dispatcher.add_handler(CallbackQueryHandler(
        handle_support_options,
        pattern='^(show_support_options|show_telebirr_info|back_to_about|stars_donation)$'
    ))

def add_stars_handlers(dispatcher):
    """Add handlers for Stars donation flow."""
    dispatcher.add_handler(CallbackQueryHandler(
        start_stars_donation,
        pattern='^start_stars_donation$'
    ))
    dispatcher.add_handler(CallbackQueryHandler(
        confirm_stars_donation,
        pattern='^confirm_stars_\d+$'
    ))

def add_payment_handlers(dispatcher):
    """Add handlers for payment processing."""
    dispatcher.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    dispatcher.add_handler(MessageHandler(Filters.successful_payment, successful_payment))

@subscription_required
def admin_command(update: Update, context: CallbackContext) -> None:
    """Handle the /admin command."""
    admin_manager = context.bot_data['admin_manager']
    admin_manager.show_admin_panel(update, context)

def handle_admin_callback(update: Update, context: CallbackContext) -> None:
    """Handle admin panel callback queries."""
    query = update.callback_query
    admin_manager = context.bot_data['admin_manager']

    if query.data == "admin_panel":
        admin_manager.show_admin_panel(update, context)
    elif query.data == "admin_stats":
        admin_manager.handle_stats(update, context)
    elif query.data == "admin_users":
        admin_manager.handle_users(update, context)
    elif query.data == "admin_restrictions":
        admin_manager.handle_restrictions(update, context)
    elif query.data == "admin_admins":
        admin_manager.handle_admin_management(update, context)
    elif query.data == "admin_broadcast":
        admin_manager.handle_broadcast(update, context)
    elif query.data.startswith("restrict_"):
        admin_manager.handle_restriction_action(update, context)
    elif query.data.startswith("admin_"):
        admin_manager.handle_admin_action(update, context)
    elif query.data.startswith("users_"):
        admin_manager.handle_user_navigation(update, context)
    elif query.data.startswith("broadcast_"):
        # Handle broadcast-related callbacks
        if query.data.startswith("broadcast_target_"):
            admin_manager.handle_broadcast_target(update, context)
        elif query.data.startswith("broadcast_select_"):
            admin_manager.handle_user_selection(update, context)
        elif query.data.startswith("broadcast_type_"):
            context.user_data['broadcast_type'] = query.data.split('_')[2]
            query.edit_message_text(
                text="📢 Please send your broadcast message now (text, photo, video, or document).\n"
                     "Send /cancel to abort the broadcast.",
                parse_mode=ParseMode.MARKDOWN
            )
        elif query.data.startswith("broadcast_users_"):
            action = query.data.split('_')[2]
            if action in ['prev', 'next']:
                context.user_data['broadcast_user_page'] = context.user_data.get('broadcast_user_page', 0) + (1 if action == 'next' else -1)
                admin_manager.show_user_selection(update, context)

    # Prevent "loading" animation from getting stuck
    if not query.data.startswith("broadcast_select_"):
        query.answer()

def handle_restriction_input(update: Update, context: CallbackContext) -> None:
    """Handle user input for restrictions."""
    admin_manager = context.bot_data['admin_manager']
    message = update.message.text

    if context.user_data.get('expecting_restriction'):
        try:
            user_id, duration, *reason = message.split()
            admin_manager.restrict_user(update, context, int(user_id), int(duration))
            update.message.reply_text(f"✅ User {user_id} has been restricted for {duration} hours.")
        except:
            update.message.reply_text("❌ Invalid format. Please use: `username/ID duration_in_hours reason`")

    elif context.user_data.get('expecting_block'):
        try:
            user_id, *reason = message.split()
            admin_manager.block_user(update, context, int(user_id))
            update.message.reply_text(f"⛔️ User {user_id} has been blocked.")
        except:
            update.message.reply_text("❌ Invalid format. Please use: `username/ID reason`")

    elif context.user_data.get('expecting_unrestrict'):
        try:
            user_id = int(message.strip())
            admin_manager.unblock_user(update, context, user_id)
            update.message.reply_text(f"✅ User {user_id} has been unrestricted.")
        except:
            update.message.reply_text("❌ Invalid format. Please use: `username/ID`")

    # Clear expectation flags
    context.user_data.pop('expecting_restriction', None)
    context.user_data.pop('expecting_block', None)
    context.user_data.pop('expecting_unrestrict', None)

@subscription_required
def model_command(update: Update, context: CallbackContext) -> None:
    """Show available AI models for paper summarization."""
    keyboard = [
        [InlineKeyboardButton("🌟 Gemini 1.5 Pro (Default) ✓", callback_data="model_gemini")],
        [InlineKeyboardButton("🤖 GPT-4 Turbo", callback_data="model_gpt4")],
        [InlineKeyboardButton("🧠 Claude 3 Opus", callback_data="model_claude3")],
        [InlineKeyboardButton("⚡ PaLM 2", callback_data="model_palm2")],
        [InlineKeyboardButton("🔮 Llama 2 70B", callback_data="model_llama2")],
        [InlineKeyboardButton("🎯 Mistral Large", callback_data="model_mistral")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = """
🤖 *AI Model Selection*

Choose your preferred AI model for paper summarization:

Current model: *Gemini 1.5 Pro* ✓

Each model has its own strengths:
• 🌟 *Gemini 1.5 Pro:* Balanced performance & efficiency
• 🤖 *GPT-4 Turbo:* Advanced reasoning & analysis
• 🧠 *Claude 3 Opus:* Detailed technical understanding
• ⚡ *PaLM 2:* Fast & efficient summarization
• 🔮 *Llama 2 70B:* Open-source powerhouse
• 🎯 *Mistral Large:* Specialized in academic content

_Note: Additional models coming soon!_
"""

    # Check if this is a callback query
    if update.callback_query:
        update.callback_query.answer()  # Answer the callback query
        update.callback_query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # This is a direct command
        update.message.reply_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

@subscription_required
def chat_command(update: Update, context: CallbackContext) -> None:
    """Start a chat session with PaperPilot."""
    if 'chat_handler' not in context.bot_data:
        context.bot_data['chat_handler'] = ChatHandler()
    context.bot_data['chat_handler'].start_chat(update, context)

def handle_chat_message(update: Update, context: CallbackContext) -> None:
    """Handle messages in chat mode."""
    if not check_channel_subscription(update, context):
        return
    if 'chat_handler' not in context.bot_data:
        context.bot_data['chat_handler'] = ChatHandler()
    context.bot_data['chat_handler'].handle_message(update, context, model)

def end_chat_command(update: Update, context: CallbackContext) -> None:
    """End the chat session."""
    if not check_channel_subscription(update, context):
        return
    if 'chat_handler' not in context.bot_data:
        context.bot_data['chat_handler'] = ChatHandler()
    context.bot_data['chat_handler'].end_chat(update, context)

def handle_model_selection(update: Update, context: CallbackContext) -> None:
    """Handle model selection callback."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    selected_model = query.data.split('_')[1]

    # For now, show that only Gemini is available
    if selected_model != 'gemini':
        message = """
⏳ *Model Not Yet Available*

This model will be integrated soon! Currently using:
🌟 *Gemini 1.5 Pro*

Stay tuned for updates!
"""
        keyboard = [[InlineKeyboardButton("« Back to Model Selection", callback_data="back_to_models")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # If Gemini is selected
    message = """
✅ *Model Selected: Gemini 1.5 Pro*

Current active model for:
• Paper summarization
• Q&A responses
• Comparative analysis

Optimized for research paper understanding!
"""
    keyboard = [[InlineKeyboardButton("« Back to Model Selection", callback_data="back_to_models")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def create_paper_keyboard(paper_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for paper actions."""
    keyboard = [
        [
            InlineKeyboardButton("📚 Read Paper", url=f"https://arxiv.org/abs/{paper_id}"),
            InlineKeyboardButton("🤖 Summarize", callback_data=f"summarize_{paper_id}")
        ],
        [
            InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{paper_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

@subscription_required
def handle_search(update: Update, context: CallbackContext) -> None:
    """Handle the /search command - provides option for simple or advanced search"""

    # If there are arguments, use the existing simple search
    if context.args:
        execute_search(update, context)  # Make sure this points to your existing search function
        return

    # If no arguments, show search options menu
    keyboard = [
        [
            InlineKeyboardButton("🔍 Simple Search", callback_data="simple_search"),
            InlineKeyboardButton("🔬 Advanced Search", callback_data="advanced_search")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "*ArXiv Paper Search*\n\n"
        "Choose your search method:\n\n"
        "🔍 *Simple Search:* Search papers directly by keywords\n"
        "🔬 *Advanced Search:* Use filters for date, author, citations, etc."
    )

    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_search_options(update: Update, context: CallbackContext) -> None:
    """Handle search option selection"""
    query = update.callback_query
    logger.info(f"Received callback query with data: {query.data}")  # Add this line

    if not check_channel_subscription(update, context):
        return

    query.answer()  # Always answer the callback query first

    try:
        if query.data == "simple_search":
            keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_search_options")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "*Enter your search terms:*\n\n"
                "📝 Type your search keywords below\n"
                "Example: `machine learning neural networks`\n\n"
                "_Hit « Back to return to search options_",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['awaiting_simple_search'] = True

        elif query.data == "advanced_search":
            # Call the advanced search menu function
            return show_advanced_search_menu(update, context)

        elif query.data == "back_to_search_options":
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Simple Search", callback_data="simple_search"),
                    InlineKeyboardButton("🔬 Advanced Search", callback_data="advanced_search")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = (
                "*ArXiv Paper Search*\n\n"
                "Choose your search method:\n\n"
                "🔍 *Simple Search:* Search papers directly by keywords\n"
                "🔬 *Advanced Search:* Use filters for date, author, citations, etc."
            )

            query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Error in handle_search_options: {str(e)}")
        query.answer("An error occurred. Please try again.")

def handle_simple_search_input(update: Update, context: CallbackContext) -> None:
    """Handle simple search input"""
    if not context.user_data.get('awaiting_simple_search'):
        return

    # Get the search query and clear the awaiting state
    query = update.message.text
    context.user_data['awaiting_simple_search'] = False

    # Delete the "Enter your search terms" message if we can find it
    if 'search_message_id' in context.user_data:
        try:
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['search_message_id']
            )
        except:
            pass  # Message might be already deleted

    # Create args for execute_search
    context.args = query.split()
    execute_search(update, context)

def handle_advanced_search_menu(update: Update, context: CallbackContext) -> int:
    """Show advanced search filters menu"""
    query = update.callback_query
    if query:
        query.answer()

    logger.info("Showing advanced search menu")  # Add logging

    # Get current filters from user data
    filters = context.user_data.get('advanced_filters', {
        'date_from': None,
        'date_to': None,
        'author': None,
        'min_citations': None,
        'categories': []
    })

    keyboard = [
        [
            InlineKeyboardButton("📅 Date Range", callback_data="filter_date"),
            InlineKeyboardButton("👤 Author", callback_data="filter_author")
        ],
        [
            InlineKeyboardButton("📊 Citations", callback_data="filter_citations"),
            InlineKeyboardButton("🔖 Categories", callback_data="filter_categories")
        ],
        [
            InlineKeyboardButton("🔍 Execute Search", callback_data="execute_search"),
            InlineKeyboardButton("« Back", callback_data="back_to_search_options")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Format current filters for display
    date_range = f"{filters['date_from']} to {filters['date_to']}" if filters['date_from'] else "Not set"
    author = filters['author'] or "Not set"
    citations = filters['min_citations'] or "Not set"
    categories = ", ".join(filters['categories']) if filters['categories'] else "Not set"

    message = (
        "*Advanced Search Filters* 🔬\n\n"
        "*Current Filters:*\n"
        f"📅 Date Range: {date_range}\n"
        f"👤 Author: {author}\n"
        f"📊 Min Citations: {citations}\n"
        f"🔖 Categories: {categories}\n\n"
        "_Select a filter to modify_"
    )

    if query:
        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    return CHOOSING_FILTER

@subscription_required
def execute_search(update: Update, context: CallbackContext) -> None:
    """Search papers on arXiv with user preferences."""
    if not context.args and 'last_search_query' not in context.user_data:
        update.message.reply_text(
            "❌ Please provide a search query!\nExample: `/search machine learning`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    query = ' '.join(context.args) if context.args else context.user_data.get('last_search_query', '')
    loading_message = update.message.reply_text("🔍 Searching papers... Please wait...")

    try:
        # Get user preferences
        pref_manager = ensure_preferences_initialized(context)
        user_prefs = pref_manager.get_preferences(update.effective_user.id)
        max_results = user_prefs.get('max_results', 10)

        # Build search query with filters
        search_query_parts = [query]  # Start with the base query

        # Add advanced filters if they exist
        if 'advanced_filters' in context.user_data:
            filters = context.user_data['advanced_filters']

            # Add date range filter
            if filters.get('date_from') and filters.get('date_to'):
                date_from = filters['date_from'].replace('-', '')
                date_to = filters['date_to'].replace('-', '')
                search_query_parts.append(f"submittedDate:[{date_from} TO {date_to}]")

            # Add author filter
            if filters.get('author'):
                author = filters['author'].strip()
                search_query_parts.append(f'au:"{author}"')

            # Add category filters - Updated for new category system
            if filters.get('categories'):
                category_filter = ' OR '.join(f'cat:{cat}' for cat in filters['categories'])
                search_query_parts.append(f"({category_filter})")

        # Combine all parts with AND
        final_query = ' AND '.join(f"({part})" for part in search_query_parts if part)

        # Log the query for debugging
        logger.info(f"Searching with query: {final_query}")

        # Create the search object
        search = arxiv.Search(
            query=final_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = list(search.results())

        if not results:
            # Provide detailed feedback
            message = (
                "❌ No papers found matching your query and filters.\n\n"
                "Try:\n"
                "• Using different search terms\n"
                "• Adjusting your category filters\n"
                "• Removing some filters\n\n"
                f"Search query: {query}\n"
            )

            # Add category information if present
            if 'advanced_filters' in context.user_data and context.user_data['advanced_filters'].get('categories'):
                cats = context.user_data['advanced_filters']['categories']
                message += f"Categories: {', '.join(cats)}\n"

            loading_message.edit_text(message)
            return

        context.user_data['search_state'] = {
            'results': results,
            'current_index': 0,
            'current_paper': None
        }

        loading_message.delete()
        show_paper_result(update, context, context.user_data['search_state'], is_new_search=True)

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        error_message = (
            "❌ An error occurred while searching.\n\n"
            "Please try:\n"
            "• Using simpler search terms\n"
            "• Reducing the number of categories\n"
            "• Checking your category selections\n\n"
            f"Error details: {str(e)}"
        )
        loading_message.edit_text(error_message)

def handle_more_results(update: Update, context: CallbackContext) -> None:
    """Handle 'More Results' button click."""
    query = update.callback_query

    if not check_channel_subscription(update, context):
        return

    if 'search_state' not in context.user_data:
        query.answer("❌ No active search session. Please start a new search.")
        return

    context.user_data['search_state']['current_index'] += 1
    current_index = context.user_data['search_state']['current_index']
    results = context.user_data['search_state']['results']

    if current_index >= len(results):
        query.answer("🏁 You've reached the end of results!")
        return

    paper = results[current_index]

    # Create keyboard with all buttons including Add to Compare
    keyboard = [
        [
            InlineKeyboardButton("📚 Read Paper", url=f"https://arxiv.org/abs/{paper.get_short_id()}"),
            InlineKeyboardButton("🤖 Summarize", callback_data=f"summarize_{paper.get_short_id()}")
        ],
        [
            InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{paper.get_short_id()}"),
            InlineKeyboardButton("➕ Add to Compare", callback_data=f"compare_add_{paper.get_short_id()}")
        ]
    ]

    # Add More Results button if there are more papers
    if current_index < len(results) - 1:
        keyboard.append([InlineKeyboardButton("➡️ More Results", callback_data="more_results")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    formatted_text = format_paper(paper)
    message = f"📚 Result {current_index + 1}/{len(results)}:\n\n{formatted_text}"

    try:
        query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Error updating message: {str(e)}")
        query.answer("❌ Error showing next result. Please try searching again.")

def show_paper_result(update: Update, context: CallbackContext, user_state, is_new_search=False):
    """Show single paper result with navigation."""
    results = user_state['results']
    current_index = user_state['current_index']

    if current_index >= len(results):
        update.message.reply_text("🏁 You've reached the end of results!")
        return

    paper = results[current_index]

    keyboard = [
    [
        InlineKeyboardButton("📚 Read Paper", url=f"https://arxiv.org/abs/{paper.get_short_id()}"),
        InlineKeyboardButton("🤖 Summarize", callback_data=f"summarize_{paper.get_short_id()}")
    ],
    [
        InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{paper.get_short_id()}"),
        InlineKeyboardButton("➕ Add to Compare", callback_data=f"compare_add_{paper.get_short_id()}")  # Fixed here
    ]
]

    if current_index < len(results) - 1:
        keyboard.append([InlineKeyboardButton("➡️ More Results", callback_data="more_results")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    formatted_text = format_paper(paper)

    if is_new_search:
        message = f"🔍 Found {len(results)} papers! Showing result {current_index + 1}/{len(results)}:\n\n{formatted_text}"
    else:
        message = f"📚 Result {current_index + 1}/{len(results)}:\n\n{formatted_text}"

    return update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

def summarize_paper(update: Update, context: CallbackContext) -> None:
    """Summarize paper and enable Q&A mode."""
    query = update.callback_query

    if not check_channel_subscription(update, context):
        return

    paper_id = query.data.split('_')[1]

    try:
        query.answer("🤖 Asking PaperPilot to analyze the paper...")
        processing_message = query.message.reply_text(
            "🧠 PaperPilot is analyzing the paper... Please wait..."
        )

        paper = next(arxiv.Search(id_list=[paper_id]).results())
        context.user_data['current_paper'] = paper
        summary = generate_paper_summary(paper)

        summary_message = f"""
*PaperPilot Summary* 🤖

{summary}

*Paper Details:*
📄 [{paper.title}]({paper.pdf_url})
👥 Authors: {', '.join(str(author) for author in paper.authors[:3])} {'...' if len(paper.authors) > 3 else ''}
📅 Published: {paper.published.strftime('%Y-%m-%d')}

💡 *Ask me anything about this paper!*
Just type your question below and I'll answer based on the paper's content.
"""

        processing_message.delete()
        query.message.reply_text(
            summary_message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as e:
        processing_message.edit_text(
            f"❌ Could not generate summary: {str(e)}\nPlease try again later."
        )
        logger.error(f"Summarization error: {str(e)}")

def download_paper(update: Update, context: CallbackContext) -> None:
    """Download and send paper as PDF using the most reliable method with pro UX."""
    query = update.callback_query

    if not check_channel_subscription(update, context):
        return

    paper_id = query.data.split('_')[1]

    try:
        # Show downloading message with cool animation
        query.answer("📥 Initiating quantum paper download...")  # Fun user feedback
        loading_message = query.message.reply_text(
            "🛸 *Beaming paper from arXiv servers...*\n"
            "_This may take a few seconds..._",
            parse_mode=ParseMode.MARKDOWN
        )

        # Fetch paper metadata (for title/authors later)
        paper = next(arxiv.Search(id_list=[paper_id]).results())

        # Method 2 (The Working Champion) - Export API
        export_url = f"https://export.arxiv.org/pdf/{paper_id}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf'
        }

        # Download with streaming
        with requests.get(
            export_url,
            headers=headers,
            stream=True,
            timeout=30
        ) as response:
            response.raise_for_status()

            # Verify it's actually a PDF
            if 'application/pdf' not in response.headers.get('content-type', '').lower():
                raise ValueError("Server returned non-PDF content")

            # Create in-memory file with progress tracking
            pdf_file = BytesIO()
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192
            progress = 0

            for chunk in response.iter_content(chunk_size):
                if chunk:
                    pdf_file.write(chunk)
                    progress += len(chunk)

                    # Update progress every 25%
                    if total_size > 0 and int((progress / total_size) * 100) % 25 == 0:
                        loading_message.edit_text(
                            f"🚀 Downloading... {int((progress / total_size) * 100)}% complete\n"
                            f"_File size: {total_size/1024/1024:.1f} MB_",
                            parse_mode=ParseMode.MARKDOWN
                        )

            pdf_file.seek(0)

            # Create sexy filename
            safe_title = "".join(
                c for c in paper.title
                if c.isalnum() or c in (' ', '-', '_')
            ).rstrip()
            filename = f"{safe_title[:45]}.pdf"  # Slightly shorter for mobile users

            # Send that beautiful PDF with style
            loading_message.delete()
            query.message.reply_document(
                document=pdf_file,
                filename=filename,
                caption=f"""
📄 *{paper.title}*
👥 *Authors:* {', '.join(str(author) for author in paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
📅 *Published:* {paper.published.strftime('%Y-%m-%d')}
🔗 *Original URL:* [arXiv:{paper_id}]({paper.pdf_url})
                """,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🌟 Rate This Paper", callback_data=f"rate_{paper_id}")
                ]])
            )

    except Exception as e:
        error_msg = f"""
❌ *Download Failed*
_But don't worry! You can still access the paper:_

🔗 [Direct PDF Link]({paper.pdf_url})
📄 [Abstract Page](https://arxiv.org/abs/{paper_id})

_Error details:_ `{str(e)}`
"""
        try:
            loading_message.edit_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except:
            query.message.reply_text(
                error_msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        logger.error(f"Paper download error for {paper_id}: {str(e)}")

def chat_about_paper(update: Update, context: CallbackContext) -> None:
    # Check if we're expecting a keyword or journal name
    if context.user_data.get('awaiting_notification_keyword') or context.user_data.get('awaiting_journal_name'):
        return  # Stop processing if we're expecting a keyword or journal name

    # Check if the user is subscribed to the channel
    if not check_channel_subscription(update, context):
        return

    # Check if there's a current paper to chat about
    if not context.user_data.get('current_paper'):
        return  # Don't show any message if there's no current paper

    # Check if the user is subscribed to the channel
    if not check_channel_subscription(update, context):
        return

    # Check if there's a current paper to chat about
    if not context.user_data.get('current_paper'):
        update.message.reply_text(
            "❌ Please summarize a paper first before asking questions about it!"
        )
        return

    # Get the paper and the user's question
    paper = context.user_data['current_paper']
    question = update.message.text

    try:
        # Show typing indicator and analyzing message
        update.message.chat.send_action(ChatAction.TYPING)
        analyzing_message = update.message.reply_text(
            "🧠 Analyzing paper to answer your question...",
            quote=True
        )

        # Create prompt for Gemini
        prompt = f"""
        Based on this research paper:
        Title: {paper.title}
        Abstract: {paper.summary}

        Please answer this question: {question}

        Rules for answering:
        1. Be accurate and specific
        2. Use information from the paper
        3. If the answer isn't in the paper, you can answer
           from your knowledge but it must be based on the paper's concept and idea.
           If the answer is in the paper, use it to answer.
        4. Use simple language but maintain technical accuracy
        5. Include relevant quotes if helpful
        6. Maintain a playful tone but professional
        7. You can answer based on the summary, not only the paper.
        """

        # Get response from Gemini
        response = model.generate_content(prompt)

        # Update the analyzing message with the answer
        analyzing_message.edit_text(
            f"""
💭 *You:*
{question}

🤖 *PaperPilot:*
{response.text}

_Ask another question or use /search to find more papers!_
            """,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        analyzing_message.edit_text(
            f"❌ Sorry, I couldn't process your question: {str(e)}"
        )
        logger.error(f"Q&A error: {str(e)}")

@subscription_required
def get_latest_papers(update: Update, context: CallbackContext) -> None:
    """Get latest papers from arXiv."""
    loading_message = update.message.reply_text("🔄 Fetching latest papers... Please wait...")

    try:
        # Use a date-based query for the last week
        from datetime import datetime, timedelta
        last_week = datetime.now() - timedelta(days=7)
        date_query = f"submittedDate:[{last_week.strftime('%Y%m%d')}0000 TO 999999999999]"

        search = arxiv.Search(
            query=date_query,
            max_results=5,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

        results = list(search.results())

        if not results:
            loading_message.edit_text("❌ Could not fetch latest papers. Please try again later.")
            return

        context.user_data['search_state'] = {
            'results': results,
            'current_index': 0,
            'current_paper': None
        }

        loading_message.delete()
        show_paper_result(update, context, context.user_data['search_state'], is_new_search=True)

    except Exception as e:
        loading_message.edit_text(f"❌ An error occurred: {str(e)}")
        logger.error(f"Latest papers error: {str(e)}")

def start_paper_comparison(update: Update, context: CallbackContext) -> None:
    """Start the paper comparison process."""
    if not check_channel_subscription(update, context):
        return

    context.user_data['papers_to_compare'] = []
    context.user_data['awaiting_paper_selection'] = True

    update.message.reply_text(
        f"""🔄 *Paper Comparison Mode*

Let's compare some papers! You can add up to {MAX_PAPERS_TO_COMPARE} papers to compare.

*How to use:*
1. Search for papers using /search as usual
2. When you see a paper you want to compare, click "➕ Add to Compare"
3. Repeat until you've added all papers
4. Click "🔍 Generate Comparison" when ready

You can use /cancel_compare to exit comparison mode.
        """,
        parse_mode=ParseMode.MARKDOWN
    )

def add_paper_to_comparison(update: Update, context: CallbackContext) -> None:
    """Add a paper to the comparison list."""
    query = update.callback_query

    if not check_channel_subscription(update, context):
        return

    if 'papers_to_compare' not in context.user_data:
        context.user_data['papers_to_compare'] = []

    paper_id = query.data.split('_')[2]  # Format: "compare_add_<paper_id>"

    try:
        paper = next(arxiv.Search(id_list=[paper_id]).results())
        papers_list = context.user_data['papers_to_compare']

        # Check if paper is already in the list
        if any(p.entry_id == paper.entry_id for p in papers_list):
            query.answer("❌ This paper is already in your comparison list!")
            return

        # Add paper to comparison list
        papers_list.append(paper)
        context.user_data['papers_to_compare'] = papers_list

        query.answer("✅ Paper added to comparison list!")
        query.message.reply_text(
            f"""📑 Paper added to comparison ({len(papers_list)}/{MAX_PAPERS_TO_COMPARE})

*Title:* {paper.title}

{f'Add {MAX_PAPERS_TO_COMPARE - len(papers_list)} more papers or use /compare to see the comparison!' if len(papers_list) < MAX_PAPERS_TO_COMPARE else 'Ready to compare! Use /compare to see the analysis.'}""",
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        query.answer(f"❌ Error adding paper: {str(e)}")
        logger.error(f"Error adding paper to comparison: {str(e)}")

def split_long_message(message: str, max_length: int = MAX_RESPONSE_LENGTH) -> List[str]:
    """Split long messages into smaller chunks for Telegram."""
    if len(message) <= max_length:
        return [message]

    chunks = []
    current_chunk = ""

    for line in message.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            current_chunk += line + '\n'
        else:
            chunks.append(current_chunk)
            current_chunk = line + '\n'

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def escape_markdown_v2(text: str) -> str:
    """Escape Markdown V2 special characters."""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    return ''.join(f'\\{c}' if c in escape_chars else c for c in str(text))

def generate_comparison(update: Update, context: CallbackContext) -> None:
    """Generate and show the comparison between selected papers."""
    if not check_channel_subscription(update, context):
        return

    # Initialize user session if needed
    if 'session' not in context.user_data:
        context.user_data['session'] = UserSession()

    session = context.user_data['session']

    # Check daily limit
    if not session.can_compare():
        update.message.reply_text(
            "📊 You've reached your daily comparison limit\\. Try again tomorrow\\!"
        )
        return

    if 'papers_to_compare' not in context.user_data or not context.user_data['papers_to_compare']:
        update.message.reply_text(
            "❌ No papers selected for comparison\\. Use /search to find papers and add them to compare\\!"
        )
        return

    papers = context.user_data['papers_to_compare']
    if len(papers) < 2:
        update.message.reply_text(
            "❌ Please add at least 2 papers to compare\\!"
        )
        return

    try:
        # Show processing message with cool loading animation
        loading_messages = [
            "🧠 Analyzing papers\\.\\.\\. please wait\\.\\.\\."
        ]
        processing_msg = update.message.reply_text(random.choice(loading_messages))

        # Try to get cached comparison
        comparison = paper_comparison.comparison_cache.get(papers)

        if not comparison:
            comparison = paper_comparison.compare_papers(papers)
            prompt = paper_comparison.generate_comparison_prompt(papers)
            ai_response = model.generate_content(prompt)
            comparison.methodology_comparison = str(ai_response.text)

        # Format papers with cool emojis
        papers_list = []
        paper_emojis = ["📘", "📗", "📙"]  # Different colors for different papers
        for i, p in enumerate(papers, 1):
            safe_title = escape_markdown_v2(str(p.title))
            emoji = paper_emojis[(i-1) % len(paper_emojis)]
            papers_list.append(f"{emoji} *Paper {i}:* {safe_title}")
        papers_text = "\n".join(papers_list)

        # Format unique aspects with themed emojis
        unique_aspects_list = []
        aspect_emojis = {
            "Paper 1": "🔵",
            "Paper 2": "🟢",
            "Paper 3": "🟡"
        }
        for i, aspects in comparison.unique_aspects.items():
            safe_aspects = [escape_markdown_v2(str(aspect)) for aspect in aspects]
            aspects_text = ", ".join(safe_aspects)
            emoji = aspect_emojis.get(i, "📌")
            unique_aspects_list.append(f"{emoji} *{escape_markdown_v2(str(i))}*\n   {aspects_text}")
        unique_aspects_text = "\n".join(unique_aspects_list)

        # Format common topics with cool bullet points
        common_topics = [escape_markdown_v2(str(topic)) for topic in comparison.common_topics]
        common_topics_text = "\n".join(f"⭐️ {topic}" for topic in common_topics)

        # Format similarity score with visual representation
        similarity_percentage = float(comparison.similarity_score)
        similarity_bars = "█" * int(similarity_percentage * 10) + "▒" * (10 - int(similarity_percentage * 10))
        safe_similarity = escape_markdown_v2(f"{similarity_percentage:.2%}")

        # Format the analysis text
        safe_analysis = escape_markdown_v2(str(comparison.methodology_comparison))

        # Build an awesome looking response
        response_parts = [
            "*PaperPilot Advanced Analysis*\n\n",

            "📚 *Papers Under Review*\n",
            f"{papers_text}\n\n",

            "🎯 *Similarity Analysis*\n",
            f"`{similarity_bars}` {safe_similarity}\n\n",

            "🌟 *Common Research Themes*\n",
            f"{common_topics_text}\n\n",

            "🔍 *Unique Contributions*\n",
            f"{unique_aspects_text}\n\n",

            "📊 *Detailed Analysis*\n",
            f"{safe_analysis}\n\n",

            "━━━━━━━━━━━━━━━\n",
            "🔄 Use /clear\\_comparison to start fresh\\!\n\n",
            "🤖 Powered by PaperPilot AI"
        ]

        response = "".join(response_parts)

        # Delete processing message
        processing_msg.delete()

        # Split and send the response with cool headers
        if len(response) > 4000:
            chunks = []
            current_chunk = ""

            for line in response.split('\n'):
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'

            if current_chunk:
                chunks.append(current_chunk)

            # Send chunks with cool headers
            for i, chunk in enumerate(chunks):
                header = f"✨ *PaperPilot Analysis \\| Part {i+1}/{len(chunks)}* ✨\n\n"
                if i == 0:
                    chunk = header + chunk
                else:
                    chunk = header + chunk

                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True
                )
                time.sleep(0.5)
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=response,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )

        # Record the comparison
        session.record_comparison()

        # Clear the comparison list
        context.user_data['papers_to_compare'] = []

    except Exception as e:
        logger.error(f"Comparison error: {str(e)}")
        if processing_msg:
            try:
                processing_msg.edit_text(
                    "❌ Oops\\! Something went wrong\\. Let's try that again\\!",
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except:
                processing_msg.edit_text(
                    "❌ Oops! Something went wrong. Let's try that again!"
                )

def safe_send_message(update: Update, context: CallbackContext, text: str, **kwargs) -> None:
    """Safely send messages with retry logic and splitting."""
    try:
        # Ensure the text is properly escaped if using markdown
        if kwargs.get('parse_mode') == ParseMode.MARKDOWN_V2:
            text = escape_markdown_v2(text)

        # Split long messages
        if len(text) > 4000:
            chunks = []
            current_chunk = ""

            for line in text.split('\n'):
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                else:
                    current_chunk += line + '\n'

            if current_chunk:
                chunks.append(current_chunk)

            # Send chunks
            for i, chunk in enumerate(chunks):
                try:
                    time.sleep(RATE_LIMIT_DELAY)
                    update.message.reply_text(chunk, **kwargs)
                except (TimedOut, NetworkError):
                    time.sleep(2)
                    update.message.reply_text(chunk, **kwargs)
                except BadRequest as e:
                    logger.error(f"Bad request error: {str(e)}")
                    # Try without markdown
                    kwargs_plain = kwargs.copy()
                    kwargs_plain.pop('parse_mode', None)
                    update.message.reply_text(chunk, **kwargs_plain)
        else:
            update.message.reply_text(text, **kwargs)

    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        try:
            update.message.reply_text(
                "❌ An unexpected error occurred\\. Please try again later\\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except:
            update.message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )

def clear_comparison(update: Update, context: CallbackContext) -> None:
    """Clear the current paper comparison list."""
    if 'papers_to_compare' in context.user_data:
        context.user_data['papers_to_compare'] = []
    update.message.reply_text(
        "🧹 Comparison list cleared! You can start a new comparison."
    )

def settings_command(update: Update, context: CallbackContext) -> None:
    """Show settings menu."""
    if not check_channel_subscription(update, context):
        return

    keyboard = [
        [
            InlineKeyboardButton("📊 Max Results", callback_data="settings_max_results"),
            InlineKeyboardButton("📚 Journals", callback_data="settings_journals")
        ],
        [
            InlineKeyboardButton("🏷️ Categories", callback_data="settings_categories")
        ],
        [
            InlineKeyboardButton("🔄 Reset Preferences", callback_data="settings_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    pref_manager = ensure_preferences_initialized(context)
    user_prefs = pref_manager.get_preferences(update.effective_user.id)

    categories_count = len(user_prefs.get('preferred_categories', []))

    message = f"""
🛠 *User Preferences*

Current Settings:
📊 Max Results: {user_prefs['max_results']}
📚 Specific Journals: {', '.join(user_prefs['specific_journals']) or 'None'}
🏷️ Categories: {categories_count} selected
⏰ Last Updated: {user_prefs['last_updated']}

Select a setting to modify:
"""

    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_settings_callback(update: Update, context: CallbackContext) -> None:
    """Handle settings menu callbacks."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    action = query.data.split('_', 1)[1]  # Split only once to handle journal names with underscores
    pref_manager = ensure_preferences_initialized(context)

    if action == "categories":
        handle_categories_menu(update, context)

    if action == "max_results":
        keyboard = [
            [
                InlineKeyboardButton("5", callback_data="set_max_results_5"),
                InlineKeyboardButton("10", callback_data="set_max_results_10"),
                InlineKeyboardButton("20", callback_data="set_max_results_20")
            ],
            [InlineKeyboardButton("« Back to Settings", callback_data="back_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        current_max = pref_manager.get_preferences(update.effective_user.id).get('max_results', 10)
        query.edit_message_text(
            f"📊 *Maximum Results Settings*\n\nCurrent setting: {current_max}\nSelect new maximum number of search results:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "journals":
        prefs = pref_manager.get_preferences(update.effective_user.id)
        journals = prefs.get('specific_journals', [])

        keyboard = []
        # Add remove buttons for existing journals
        for journal in journals:
            safe_journal = journal.replace(' ', '_')  # Make safe for callback data
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ Remove {journal}",
                    callback_data=f"journal_remove_{safe_journal}"
                )
            ])

        # Add other buttons
        keyboard.extend([
            [InlineKeyboardButton("➕ Add New Journal", callback_data="journal_add")],
            [InlineKeyboardButton("« Back to Settings", callback_data="back_settings")]
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = "📚 *Journal Preferences*\n\n"
        message += "*Current journals:*\n"
        if journals:
            message += "\n".join([f"• {j}" for j in journals])
        else:
            message += "_No journals selected_"

        message += "\n\nClick '➕ Add New Journal' to add a new journal or click the ❌ button to remove a journal."

        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "reset":
        # Reset preferences to default
        default_prefs = {
            'max_results': 10,
            'specific_journals': [],
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'auto_download': False,
            'preferred_categories': []
        }
        pref_manager.save_preferences(update.effective_user.id, default_prefs)

        query.edit_message_text(
            "✅ Preferences reset to default values!\n\nUse /settings to view or modify settings.",
            parse_mode=ParseMode.MARKDOWN
        )

def handle_journal_actions(update: Update, context: CallbackContext) -> None:
    """Handle journal add/remove actions."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    pref_manager = ensure_preferences_initialized(context)
    action = query.data.split('_', 2)  # Split into ['journal', 'action', 'name']

    if len(action) < 2:
        return

    if action[1] == "remove":
        # Remove journal
        journal_name = action[2].replace('_', ' ')  # Convert back from safe format
        prefs = pref_manager.get_preferences(update.effective_user.id)
        if journal_name in prefs['specific_journals']:
            prefs['specific_journals'].remove(journal_name)
            pref_manager.save_preferences(update.effective_user.id, prefs)

        # Refresh journals menu
        query.data = "settings_journals"
        handle_settings_callback(update, context)

    elif action[1] == "add":
        keyboard = [[InlineKeyboardButton("« Back to Journals", callback_data="settings_journals")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "📝 *Add New Journal*\n\n"
            "To add a new journal, send the journal name as a message.\n\n"
            "Example: `Nature` or `Science`\n\n"
            "_Click 'Back to Journals' to cancel_",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        # Set state to expect journal name
        context.user_data['awaiting_journal_name'] = True

def handle_back_to_settings(update: Update, context: CallbackContext) -> None:
    """Handle back to settings button."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    # Show main settings menu
    pref_manager = ensure_preferences_initialized(context)
    user_prefs = pref_manager.get_preferences(update.effective_user.id)

    keyboard = [
        [
            InlineKeyboardButton("📊 Max Results", callback_data="settings_max_results"),
            InlineKeyboardButton("📚 Journals", callback_data="settings_journals")
        ],
        [
            InlineKeyboardButton("🔄 Reset Preferences", callback_data="settings_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""
🛠 *User Preferences*

Current Settings:
📊 Max Results: {user_prefs['max_results']}
📚 Specific Journals: {', '.join(user_prefs['specific_journals']) or 'None'}
⏰ Last Updated: {user_prefs['last_updated']}

Select a setting to modify:
"""

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_journal_name_message(update: Update, context: CallbackContext) -> None:
    # Check if we're expecting a journal name
    if not context.user_data.get('awaiting_journal_name'):
        return None  # Let other handlers process the message

    # Get the journal name from the user's message
    journal_name = update.message.text.strip()
    pref_manager = ensure_preferences_initialized(context)
    prefs = pref_manager.get_preferences(update.effective_user.id)

    if journal_name in prefs['specific_journals']:
        update.message.reply_text(
            f"❌ '{journal_name}' is already in your preferred journals!\n\n"
            "Use /settings to view your journals.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        prefs['specific_journals'].append(journal_name)
        pref_manager.save_preferences(update.effective_user.id, prefs)

        update.message.reply_text(
            f"✅ Added '{journal_name}' to your preferred journals!\n\n"
            "Use /settings to view all preferences.",
            parse_mode=ParseMode.MARKDOWN
        )

    # Clear the awaiting state
    context.user_data['awaiting_journal_name'] = False
    return True  # Stop other handlers from processing this message

def handle_max_results_callback(update: Update, context: CallbackContext) -> None:
    """Handle selection of maximum results."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    # Extract the number from callback data
    max_results = int(query.data.split('_')[-1])
    pref_manager = ensure_preferences_initialized(context)

    # Update user preference
    prefs = pref_manager.get_preferences(update.effective_user.id)
    prefs['max_results'] = max_results
    pref_manager.save_preferences(update.effective_user.id, prefs)

    # Show confirmation and return to settings
    query.edit_message_text(
        f"✅ Maximum results updated to: {max_results}\n\nUse /settings to view or modify other settings.",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_categories_menu(update: Update, context: CallbackContext) -> None:
    """Show categories menu."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    pref_manager = ensure_preferences_initialized(context)
    user_prefs = pref_manager.get_preferences(update.effective_user.id)
    selected_categories = set(user_prefs.get('preferred_categories', []))

    # Create keyboard with categories grouped by main field
    keyboard = []
    for field, categories in UserPreferences.ARXIV_CATEGORIES.items():
        # Add field header
        keyboard.append([InlineKeyboardButton(
            f"📚 {field}",
            callback_data=f"category_field_{field}"
        )])

    keyboard.append([InlineKeyboardButton("« Back to Settings", callback_data="back_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    current_cats = user_prefs.get('preferred_categories', [])
    categories_text = "\n".join([f"• {cat}" for cat in current_cats]) if current_cats else "None selected"

    message = f"""
🏷️ *Category Preferences*

Selected Categories:
{categories_text}

Choose a field to view categories:
"""

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_category_field(update: Update, context: CallbackContext) -> None:
    """Show categories for selected field."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    field = query.data.split('_')[2]
    categories = UserPreferences.ARXIV_CATEGORIES[field]

    pref_manager = ensure_preferences_initialized(context)
    user_prefs = pref_manager.get_preferences(update.effective_user.id)
    selected_categories = set(user_prefs.get('preferred_categories', []))

    keyboard = []
    # Add category toggles
    for cat_id, cat_name in categories.items():
        status = "✅" if cat_id in selected_categories else "⭕️"
        keyboard.append([InlineKeyboardButton(
            f"{status} {cat_name} ({cat_id})",
            callback_data=f"toggle_category_{cat_id}"
        )])

    # Add navigation buttons
    keyboard.append([
        InlineKeyboardButton("« Back to Fields", callback_data="settings_categories"),
        InlineKeyboardButton("« Main Menu", callback_data="back_settings")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""
🏷️ *{field} Categories*

Click a category to toggle selection:
✅ = Selected
⭕️ = Not Selected

Your selections will be used to filter search results.
"""

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_category_toggle(update: Update, context: CallbackContext) -> None:
    """Toggle category selection."""
    query = update.callback_query
    query.answer()

    if not check_channel_subscription(update, context):
        return

    category_id = query.data.split('_')[2]
    pref_manager = ensure_preferences_initialized(context)
    prefs = pref_manager.get_preferences(update.effective_user.id)

    if 'preferred_categories' not in prefs:
        prefs['preferred_categories'] = []

    if category_id in prefs['preferred_categories']:
        prefs['preferred_categories'].remove(category_id)
        query.answer("Category removed!")
    else:
        prefs['preferred_categories'].append(category_id)
        query.answer("Category added!")

    pref_manager.save_preferences(update.effective_user.id, prefs)

    # Find which field this category belongs to
    for field, categories in UserPreferences.ARXIV_CATEGORIES.items():
        if category_id in categories:
            query.data = f"category_field_{field}"
            handle_category_field(update, context)
            break

def sanitize_search_query(query: str) -> str:
    """Clean and validate the search query."""
    # Remove any problematic characters
    query = query.replace('"', '\"')
    query = query.replace('\'', '')
    return query

def format_category_id(category_id: str) -> str:
    """Format category ID for arXiv search."""
    # Ensure category ID is properly formatted
    return category_id.lower().strip()

def ensure_preferences_initialized(context: CallbackContext) -> UserPreferences:
    """Ensure preferences manager is initialized and return it."""
    if 'preferences_manager' not in context.bot_data:
        global preferences_manager
        if not globals().get('preferences_manager'):
            preferences_manager = UserPreferences()
        context.bot_data['preferences_manager'] = preferences_manager
    return context.bot_data['preferences_manager']


def setup_notifications(update: Update, context: CallbackContext) -> None:
    """Setup notification preferences."""
    if not check_channel_subscription(update, context):
        return

    keyboard = [
        [
            InlineKeyboardButton("🔔 Enable", callback_data="notif_enable"),
            InlineKeyboardButton("🔕 Disable", callback_data="notif_disable")
        ],
        [
            InlineKeyboardButton("📅 Daily", callback_data="notif_freq_daily"),
            InlineKeyboardButton("📅 Weekly", callback_data="notif_freq_weekly")
        ],
        [
            InlineKeyboardButton("➕ Add Keyword", callback_data="notif_add_keyword"),
            InlineKeyboardButton("❌ Remove Keyword", callback_data="notif_remove_keyword")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    notif_manager = NotificationPreferences()
    prefs = notif_manager.get_preferences(update.effective_user.id)

    status = "✅ Enabled" if prefs['enabled'] else "❌ Disabled"
    keywords = ", ".join(prefs['keywords']) if prefs['keywords'] else "None"

    message = f"""
🔔 *Notification Settings*

Status: {status}
Frequency: {prefs['frequency'].title()}
Keywords: {keywords}
Time: {prefs['notification_time']} UTC

Choose an option to modify:
"""

    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def handle_notification_keyword(update: Update, context: CallbackContext) -> None:
    # Check if we're expecting a keyword
    if not context.user_data.get('awaiting_notification_keyword'):
        return None  # Let other handlers process the message

    # Get the keyword from the user's message
    keyword = update.message.text.strip().lower()

    # Add the keyword to the user's preferences
    notif_manager = NotificationPreferences()
    notif_manager.add_keyword(update.effective_user.id, keyword)

    # Clear the awaiting state
    context.user_data['awaiting_notification_keyword'] = False

    # Send a success message
    update.message.reply_text(
        f"✅ Successfully added keyword: *{keyword}*\n\n"
        "Use /notifications to view your updated notification settings.",
        parse_mode=ParseMode.MARKDOWN
    )

    return True  # Stop other handlers from processing this message

def handle_notification_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    try:
        if not query:
            return

        query.answer()  # Answer callback immediately to prevent "loading" state

        if not check_channel_subscription(update, context):
            return

        notif_manager = NotificationPreferences()
        prefs = notif_manager.get_preferences(update.effective_user.id)

        # Initialize preferences if they don't exist
        if not prefs:
            prefs = {
                'enabled': False,
                'frequency': 'daily',
                'keywords': [],
                'notification_time': '09:00'
            }
            notif_manager.save_preferences(update.effective_user.id, prefs)

        # Handle back button - Important: Check this first
        if query.data in ["back_to_notifications", "back_notifications", "back"]:
            show_notifications_menu(update, context)
            return

        # Handle other callbacks
        if query.data == "notif_remove":
            keywords = prefs.get('keywords', [])
            if not keywords:
                show_notifications_menu(update, context, "❌ No keywords to remove!")
                return

            keyboard = []
            for keyword in keywords:
                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ {keyword}",
                        callback_data=f"notif_remove_keyword_{keyword}"
                    )
                ])

            keyboard.append([InlineKeyboardButton("« Back to Settings", callback_data="back_to_notifications")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = "*Remove Keywords*\n\nSelect a keyword to remove:\n\n"
            text += "\n".join([f"• {kw}" for kw in keywords])

            query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        elif query.data == "notif_add":
            context.user_data['awaiting_notification_keyword'] = True
            keyboard = [[InlineKeyboardButton("« Back to Settings", callback_data="back_to_notifications")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = (
                "*Add New Keyword*\n\n"
                "Please send the keyword you want to be notified about.\n\n"
                "*Examples:*\n"
                "• machine learning\n"
                "• neural networks\n"
                "• quantum computing\n\n"
                "_Click 'Back to Settings' to cancel_"
            )

            query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        elif query.data.startswith("notif_remove_keyword_"):
            keyword = query.data.replace("notif_remove_keyword_", "")
            if keyword in prefs.get('keywords', []):
                prefs['keywords'].remove(keyword)
                notif_manager.save_preferences(update.effective_user.id, prefs)
                show_notifications_menu(update, context, f"✅ Removed keyword: {keyword}")
            else:
                show_notifications_menu(update, context, "❌ Keyword not found!")
            return

        elif query.data == "notif_enable":
            prefs['enabled'] = True
            notif_manager.save_preferences(update.effective_user.id, prefs)
            show_notifications_menu(update, context, "✅ Notifications enabled!")

        elif query.data == "notif_disable":
            prefs['enabled'] = False
            notif_manager.save_preferences(update.effective_user.id, prefs)
            show_notifications_menu(update, context, "🔕 Notifications disabled!")

        elif query.data.startswith("notif_freq_"):
            freq = query.data.replace("notif_freq_", "")
            prefs['frequency'] = freq
            notif_manager.save_preferences(update.effective_user.id, prefs)
            show_notifications_menu(update, context, f"📅 Frequency set to {freq}!")

    except Exception as e:
        logger.error(f"Error in notification callback: {str(e)}")
        try:
            show_notifications_menu(update, context, "❌ An error occurred. Please try again.")
        except:
            if update.effective_message:
                update.effective_message.reply_text("❌ An error occurred. Please use /notifications to start over.")

def show_notifications_menu(update: Update, context: CallbackContext, status_message: str = None) -> None:
    """Show the notifications menu with current settings."""
    try:
        # Get or initialize preferences
        notif_manager = NotificationPreferences()
        prefs = notif_manager.get_preferences(update.effective_user.id)

        # Initialize preferences if they don't exist
        if not prefs:
            prefs = {
                'enabled': False,
                'frequency': 'daily',
                'keywords': [],
                'notification_time': '09:00'
            }
            notif_manager.save_preferences(update.effective_user.id, prefs)

        # Clear any awaiting states
        if 'awaiting_notification_keyword' in context.user_data:
            del context.user_data['awaiting_notification_keyword']

        # Create keyboard with explicit callback data
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔔 Enable" if not prefs.get('enabled', False) else "🔕 Disable",
                    callback_data="notif_enable" if not prefs.get('enabled', False) else "notif_disable"
                )
            ],
            [
                InlineKeyboardButton("📅 Daily", callback_data="notif_freq_daily"),
                InlineKeyboardButton("📅 Weekly", callback_data="notif_freq_weekly")
            ],
            [
                InlineKeyboardButton("➕ Add Keyword", callback_data="notif_add"),
                InlineKeyboardButton("❌ Remove Keyword", callback_data="notif_remove")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Prepare message text
        status = "✅ Enabled" if prefs.get('enabled', False) else "❌ Disabled"
        keywords = ", ".join(prefs.get('keywords', [])) if prefs.get('keywords', []) else "None"

        message = f"""
🔔 *Notification Settings*

Status: {status}
Frequency: {prefs.get('frequency', 'daily').title()}
Keywords: {keywords}
Time: {prefs.get('notification_time', '09:00')} UTC

_All buttons are clickable - tap any option to change settings_
"""

        if status_message:
            message = f"{status_message}\n\n{message}"

        # Send or edit message
        if update.callback_query:
            update.callback_query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in show_notifications_menu: {str(e)}")
        try:
            text = "❌ An error occurred. Please use /notifications to start over."
            if update.callback_query:
                update.callback_query.edit_message_text(text)
            else:
                update.message.reply_text(text)
        except:
            pass

def check_notifications(context: CallbackContext) -> None:
    """Check and send notifications to users."""
    job = context.job
    notif_manager = NotificationPreferences()

    # Get all notification files
    for filename in os.listdir(notif_manager.notifications_dir):
        if not filename.startswith("notifications_"):
            continue

        try:
            user_id = int(filename.split('_')[1].split('.')[0])
            prefs = notif_manager.get_preferences(user_id)

            if not prefs['enabled'] or not notif_manager.should_notify(user_id):
                continue

            # Search for new papers
            search_query_parts = []

            # Add keywords
            for keyword in prefs['keywords']:
                search_query_parts.append(keyword)

            # Add categories if any
            if prefs['categories']:
                category_filter = ' OR '.join(f'cat:{cat}' for cat in prefs['categories'])
                search_query_parts.append(f"({category_filter})")

            # Get papers from last day/week
            time_window = 7 if prefs['frequency'] == 'weekly' else 1
            last_check = datetime.strptime(prefs['last_checked'], '%Y-%m-%d %H:%M:%S')

            query = ' AND '.join(f"({part})" for part in search_query_parts if part)
            search = arxiv.Search(
                query=query,
                max_results=10,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            results = list(search.results())
            new_papers = []

            for paper in results:
                if paper.published.replace(tzinfo=None) > last_check:
                    new_papers.append(paper)

            if new_papers:
                # Send notification
                message = f"🔔 *New Papers Alert!*\n\nFound {len(new_papers)} new papers matching your interests:\n\n"

                for i, paper in enumerate(new_papers[:5], 1):
                    message += f"{i}. [{paper.title}]({paper.pdf_url})\n"

                if len(new_papers) > 5:
                    message += f"\n_...and {len(new_papers) - 5} more papers_"

                context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )

            # Update last checked time
            prefs['last_checked'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            prefs['last_notification'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            notif_manager.save_preferences(user_id, prefs)

        except Exception as e:
            logger.error(f"Error processing notifications for user {user_id}: {str(e)}")


def main() -> None:
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    advanced_search_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_advanced_search_menu, pattern='^advanced_search$')
        ],
        states={
            CHOOSING_FILTER: [
                CallbackQueryHandler(handle_filter_selection, pattern='^filter_'),
                CallbackQueryHandler(handle_filter_execute, pattern='^execute_search$'),
                CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_filters$'),
                CallbackQueryHandler(handle_main_category_selection, pattern='^cat_main_'),
                CallbackQueryHandler(handle_subcategory_selection, pattern='^cat_sub_'),
                CallbackQueryHandler(handle_category_toggle, pattern='^cat_toggle_')
            ],
            ENTER_DATE_FROM: [
                CallbackQueryHandler(handle_date_input, pattern='^date_'),
                MessageHandler(Filters.text & ~Filters.command, handle_custom_date_message),  # Add this
                CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_filters$')
            ],
            ENTER_DATE_TO: [
                MessageHandler(Filters.text & ~Filters.command, handle_custom_date_message),  # Add this
                CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_filters$')
            ],
            ENTER_AUTHOR: [
                CallbackQueryHandler(handle_author_input, pattern='^author_'),
                MessageHandler(Filters.text & ~Filters.command, handle_author_input),  # Add this
                CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_filters$')
            ],
            ENTER_MIN_CITATIONS: [
                CallbackQueryHandler(handle_citations_input, pattern='^citations_'),
                CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_filters$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_search, pattern='^back_to_main$'),
            CallbackQueryHandler(show_advanced_search_menu, pattern='^back_to_search_options$'),
            CommandHandler('cancel', cancel_search)  # Add this
        ],
        name="advanced_search"
    )

    dp.add_handler(advanced_search_handler, group=1)

    notification_handler = MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        handle_notification_keyword
    )
    dp.add_handler(notification_handler)

    document_handler = DocumentHandler()

    dp.add_handler(CommandHandler("analyze", document_handler.start))
    dp.add_handler(MessageHandler(Filters.document, document_handler.handle_document))
    dp.add_handler(CallbackQueryHandler(document_handler.handle_document_query, pattern=r'^doc_.*'))
    dp.add_handler(CallbackQueryHandler(document_handler.handle_analysis_query, pattern=r'analysis_.*'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, document_handler.handle_text_query))

    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        handle_stars_amount),
        group=1
    )

    # Payment handlers
    dp.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    dp.add_handler(MessageHandler(Filters.successful_payment, successful_payment))

    # Initialize preferences manager
    global preferences_manager
    preferences_manager = UserPreferences()
    dp.bot_data['preferences_manager'] = preferences_manager

    admin_manager = AdminManager()
    dp.bot_data['admin_manager'] = admin_manager

    dp.add_handler(CommandHandler("admin", admin_command))
    dp.add_handler(CallbackQueryHandler(handle_admin_callback, pattern="^admin_"))

    voice_handler = VoiceSearchHandler()
    dp.bot_data['chat_handler'] = ChatHandler()

    # Add command handlers
    dp.add_handler(CommandHandler("start", start), group=2)
    dp.add_handler(CommandHandler("help", help_command), group=2)
    dp.add_handler(CommandHandler("search", handle_search), group=2)
    dp.add_handler(CommandHandler("about", about_command), group=2)
    add_support_handlers(dp)
    add_support_handlers(dp)
    add_stars_handlers(dp)
    add_payment_handlers(dp)
    dp.add_handler(CommandHandler("latest", get_latest_papers), group=2)
    dp.add_handler(CommandHandler("compare", generate_comparison), group=2)
    dp.add_handler(CommandHandler("clear_comparison", clear_comparison), group=2)
    dp.add_handler(CommandHandler("settings", settings_command), group=2)
    dp.add_handler(CommandHandler("notifications", setup_notifications), group=2)
    dp.add_handler(CommandHandler("notifications", show_notifications_menu), group=2)
    dp.add_handler(CommandHandler("model", model_command))
    dp.add_handler(CallbackQueryHandler(model_command, pattern="^back_to_models$"))
    dp.add_handler(CallbackQueryHandler(handle_model_selection, pattern="^model_"))

    # Add callback handlers
    dp.add_handler(CallbackQueryHandler(handle_notification_callback))
    dp.add_handler(CallbackQueryHandler(handle_notification_callback, pattern="^notif_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_settings_callback, pattern="^settings_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_max_results_callback, pattern="^set_max_results_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_journal_actions, pattern="^journal_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_back_to_settings, pattern="^back_settings$"), group=2)
    dp.add_handler(CallbackQueryHandler(summarize_paper, pattern="^summarize_"), group=2)
    dp.add_handler(CallbackQueryHandler(download_paper, pattern="^download_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_more_results, pattern="^more_results"), group=2)
    dp.add_handler(CallbackQueryHandler(add_paper_to_comparison, pattern="^compare_add_"), group=2)
    dp.add_handler(CallbackQueryHandler(voice_handler.handle_voice_callback, pattern='^(retry|edit|search)_voice_'))
    dp.add_handler(CallbackQueryHandler(handle_categories_menu, pattern="^settings_categories$"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_category_field, pattern="^category_field_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_category_toggle, pattern="^toggle_category_"), group=2)
    dp.add_handler(CallbackQueryHandler(handle_notification_callback, pattern="^keyword_"), group=2)


    dp.add_handler(CallbackQueryHandler(end_chat_command, pattern="^end_chat$"))

    # Add chat handlers
    dp.add_handler(CommandHandler("chat", chat_command))
    dp.add_handler(CommandHandler("endchat", end_chat_command))
    dp.add_handler(CallbackQueryHandler(end_chat_command, pattern="^end_chat$"), group=2)

    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & (
            Filters.regex(r'expecting_restriction') |
            Filters.regex(r'expecting_block') |
            Filters.regex(r'expecting_unrestrict') |
            Filters.regex(r'expecting_admin_add') |
            Filters.regex(r'expecting_admin_remove')
        ),
        handle_restriction_input
    ))


    # Add chat message handler with lower priority than other handlers
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        handle_chat_message
    ), group=5)  # Higher group number means lower priority

    dp.add_handler(CallbackQueryHandler(
        handle_search_options,
        pattern='^(simple_search|advanced_search|back_to_search_options)$'
    ), group=2)  # Using group=-1 to ensure this runs before others



    # Make sure simple search input handler has lower priority
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & ~Filters.regex('^/'),
        handle_simple_search_input
    ), group=4)

    # Add journal name handler (medium priority)
    journal_handler = MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        lambda u, c: handle_journal_name_message(u, c) if not c.user_data.get('awaiting_notification_keyword') else None
    )
    dp.add_handler(journal_handler, group=2)

    # Add general chat handler (lowest priority)
    chat_handler = MessageHandler(
        Filters.text & ~Filters.command & Filters.chat_type.private,
        lambda u, c: chat_about_paper(u, c) if not (
            c.user_data.get('awaiting_notification_keyword') or
            c.user_data.get('awaiting_journal_name')
        ) else None
    )
    dp.add_handler(chat_handler, group=3)

    # Add voice handler
    dp.add_handler(MessageHandler(
        Filters.voice & Filters.chat_type.private,
        voice_handler.process_voice
    ))


    # Start the Bot
    updater.start_polling()
    logger.info("✨ ArXiv Research Assistant is online! 🚀")
    updater.idle()

if __name__ == '__main__':
    main()