from datetime import datetime, timedelta
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler
from telegram.error import BadRequest
from arxiv_categories import ARXIV_CATEGORIES

logger = logging.getLogger(__name__)

CHOOSING_FILTER, ENTER_DATE_FROM, ENTER_DATE_TO, ENTER_AUTHOR, ENTER_MIN_CITATIONS, SAVE_FILTER = range(6)

def initialize_filters(context: CallbackContext) -> None:
    if 'advanced_filters' not in context.user_data:
        context.user_data['advanced_filters'] = {
            'date_from': None,
            'date_to': None,
            'author': None,
            'min_citations': None,
            'categories': []
        }

def show_advanced_search_menu(update: Update, context: CallbackContext, execute_search_func=None) -> int:
    logger.info("Showing advanced search menu")

    query = update.callback_query
    if query:
        try:
            query.answer()
        except Exception as e:
            logger.error(f"Error answering callback query: {str(e)}")

    try:
        if 'advanced_filters' not in context.user_data:
            context.user_data['advanced_filters'] = {
                'date_from': None,
                'date_to': None,
                'author': None,
                'min_citations': None,
                'categories': []
            }

        filters = context.user_data['advanced_filters']

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

        date_range = "Not set"
        if filters.get('date_from') and filters.get('date_to'):
            date_range = f"{filters['date_from']} to {filters['date_to']}"

        author = filters.get('author', "Not set")
        citations = filters.get('min_citations', "Not set")
        categories = ", ".join(filters.get('categories', [])) or "Not set"

        message = (
            "*Advanced Search Filters* 🔬\n\n"
            "*Current Filters:*\n"
            f"📅 Date Range: {date_range}\n"
            f"👤 Author: {author}\n"
            f"📊 Min Citations: {citations}\n"
            f"🔖 Categories: {categories}\n\n"
            "_Select a filter to modify_"
        )

        message += f"\n\n_{datetime.utcnow().strftime('%H:%M:%S.%f')[:10]}_"

        if query:
            try:
                query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    logger.error(f"BadRequest error: {str(e)}")
                    raise
        else:
            update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        logger.info("Advanced search menu displayed successfully")
        return CHOOSING_FILTER

    except Exception as e:
        logger.error(f"Error showing advanced search menu: {str(e)}", exc_info=True)
        error_message = (
            "❌ An error occurred while displaying the advanced search menu.\n"
            "Please try using /search again."
        )

        try:
            if query:
                query.edit_message_text(
                    error_message,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back to Search", callback_data="back_to_search_options")
                    ]]),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                update.message.reply_text(error_message)
        except Exception as e2:
            logger.error(f"Error sending error message: {str(e2)}")

        return ConversationHandler.END

def handle_filter_selection(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    logger.info(f"Filter selection callback received: {query.data}")

    try:
        query.answer()
        initialize_filters(context)

        if query.data == "filter_date":
            keyboard = [
                [
                    InlineKeyboardButton("Last Week", callback_data="date_week"),
                    InlineKeyboardButton("Last Month", callback_data="date_month")
                ],
                [
                    InlineKeyboardButton("Last Year", callback_data="date_year"),
                    InlineKeyboardButton("Custom", callback_data="date_custom")
                ],
                [InlineKeyboardButton("« Back", callback_data="back_to_filters")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            current_filter = ""
            if context.user_data['advanced_filters'].get('date_from') and context.user_data['advanced_filters'].get('date_to'):
                current_filter = f"\nCurrent: {context.user_data['advanced_filters']['date_from']} to {context.user_data['advanced_filters']['date_to']}"

            query.edit_message_text(
                f"*Select Date Range* 📅{current_filter}\n\n"
                "Choose a predefined range or select 'Custom' to enter specific dates.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return ENTER_DATE_FROM

        elif query.data == "filter_author":
            logger.info("Showing author search options")
            keyboard = [
                [
                    InlineKeyboardButton("Exact Match", callback_data="author_exact"),
                    InlineKeyboardButton("Last Name", callback_data="author_last")
                ],
                [InlineKeyboardButton("« Back", callback_data="back_to_filters")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "*Choose Author Search Type* 👤\n\n"
                "• *Exact Match:* Search for exact author name\n"
                "• *Last Name:* Search by last name only\n",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return ENTER_AUTHOR

        elif query.data == "filter_categories":
            logger.info("Showing categories options")
            keyboard = []

            for main_category in ARXIV_CATEGORIES.keys():
                keyboard.append([InlineKeyboardButton(
                    f"📚 {main_category}",
                    callback_data=f"cat_main_{main_category}"
                )])

            keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_filters")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            current_categories = context.user_data['advanced_filters'].get('categories', [])
            selected_cats = ", ".join(current_categories) if current_categories else "None selected"

            message = f"""
*Select Categories* 🔖

Currently selected: {selected_cats}

Choose a main category to explore:
• Physics (astro-ph, cond-mat, etc.)
• Mathematics (math.AG, math.AT, etc.)
• Computer Science (cs.AI, cs.LG, etc.)
And more...

✅ = Selected
⭕️ = Not Selected
"""
            query.edit_message_text(
                message,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return CHOOSING_FILTER

    except Exception as e:
        logger.error(f"Error in filter selection: {str(e)}", exc_info=True)

def handle_main_category_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    main_category = query.data.split('_')[2]
    keyboard = []

    for category_id, category_data in ARXIV_CATEGORIES[main_category].items():
        if category_data['subcategories']:
            keyboard.append([InlineKeyboardButton(
                f"📂 {category_data['name']} ({category_id})",
                callback_data=f"cat_sub_{category_id}"
            )])
        else:
            is_selected = category_id in context.user_data.get('advanced_filters', {}).get('categories', [])
            status = "✅" if is_selected else "⭕️"
            keyboard.append([InlineKeyboardButton(
                f"{status} {category_data['name']} ({category_id})",
                callback_data=f"cat_toggle_{category_id}"
            )])

    keyboard.append([InlineKeyboardButton("« Back to Categories", callback_data="filter_categories")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""
*{main_category} Categories* 📚

Select a category to see its subcategories or toggle selection.
✅ = Selected
⭕️ = Not Selected
"""

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return CHOOSING_FILTER

def handle_subcategory_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    category_id = query.data.split('_')[2]
    keyboard = []

    for main_cat, categories in ARXIV_CATEGORIES.items():
        if category_id in categories:
            subcategories = categories[category_id]['subcategories']
            for sub_id, sub_name in subcategories.items():
                is_selected = sub_id in context.user_data.get('advanced_filters', {}).get('categories', [])
                status = "✅" if is_selected else "⭕️"
                keyboard.append([InlineKeyboardButton(
                    f"{status} {sub_name} ({sub_id})",
                    callback_data=f"cat_toggle_{sub_id}"
                )])
            break

    keyboard.append([InlineKeyboardButton("« Back", callback_data=f"cat_main_{main_cat}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""
*Subcategories* 📂

Select subcategories to include in your search:
✅ = Selected
⭕️ = Not Selected
"""

    query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return CHOOSING_FILTER

def handle_category_toggle(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    category_id = query.data.split('_')[2]

    if 'advanced_filters' not in context.user_data:
        context.user_data['advanced_filters'] = {'categories': []}
    if 'categories' not in context.user_data['advanced_filters']:
        context.user_data['advanced_filters']['categories'] = []

    categories = context.user_data['advanced_filters']['categories']

    if category_id in categories:
        categories.remove(category_id)
        feedback = f"❌ Removed {category_id}"
    else:
        categories.append(category_id)
        feedback = f"✅ Added {category_id}"

    query.answer(feedback)

    for main_cat, categories in ARXIV_CATEGORIES.items():
        for cat_id, cat_data in categories.items():
            if category_id == cat_id:
                query.data = f"cat_main_{main_cat}"
                return handle_main_category_selection(update, context)
            elif category_id in cat_data['subcategories']:
                query.data = f"cat_sub_{cat_id}"
                return handle_subcategory_selection(update, context)

    return CHOOSING_FILTER

def handle_date_input(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    logger.info(f"Processing date input: {query.data}")

    try:
        initialize_filters(context)

        if not query.data.startswith("date_"):
            return CHOOSING_FILTER

        option = query.data.split("_")[1]
        end_date = datetime.utcnow()

        if option in ["week", "month", "year"]:
            if option == "week":
                start_date = end_date - timedelta(days=7)
                date_description = "Last Week"
            elif option == "month":
                start_date = end_date - timedelta(days=30)
                date_description = "Last Month"
            else:
                start_date = end_date - timedelta(days=365)
                date_description = "Last Year"

            context.user_data['advanced_filters']['date_from'] = start_date.strftime('%Y-%m-%d')
            context.user_data['advanced_filters']['date_to'] = end_date.strftime('%Y-%m-%d')

            return show_advanced_search_menu(update, context)

        elif option == "custom":
            keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_filters")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "*Enter Start Date* 📅\n\n"
                "Please enter the start date in YYYY-MM-DD format:\n"
                "Example: `2024-01-01`",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['awaiting_custom_date'] = True
            context.user_data['advanced_filters']['date_from'] = None
            context.user_data['advanced_filters']['date_to'] = None
            return ENTER_DATE_FROM

        return CHOOSING_FILTER

    except Exception as e:
        logger.error(f"Error handling date input: {str(e)}")
        query.edit_message_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_filters")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return CHOOSING_FILTER

def handle_custom_date_message(update: Update, context: CallbackContext) -> int:
    try:
        input_date = update.message.text.strip()
        datetime.strptime(input_date, '%Y-%m-%d')

        if 'awaiting_date_to' in context.user_data:
            context.user_data['advanced_filters']['date_to'] = input_date
            del context.user_data['awaiting_date_to']

            date_from = context.user_data['advanced_filters']['date_from']
            update.message.reply_text(
                f"✅ Date range set: {date_from} to {input_date}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back to Filters", callback_data="back_to_filters")
                ]])
            )
            return CHOOSING_FILTER
        else:
            context.user_data['advanced_filters']['date_from'] = input_date
            context.user_data['awaiting_date_to'] = True

            update.message.reply_text(
                "*Enter End Date* 📅\n\n"
                "Please enter the end date in YYYY-MM-DD format:\n"
                "Example: `2024-01-31`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="back_to_filters")
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return ENTER_DATE_TO

    except ValueError:
        update.message.reply_text(
            "❌ Invalid date format! Please use YYYY-MM-DD format.\n"
            "Example: 2024-01-01",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_filters")
            ]])
        )
        return ENTER_DATE_FROM if 'awaiting_date_to' not in context.user_data else ENTER_DATE_TO

def handle_author_input(update: Update, context: CallbackContext) -> int:
    try:
        if update.callback_query:
            query = update.callback_query
            query.answer()

            if query.data.startswith("author_"):
                author_type = query.data.split("_")[1]
                context.user_data['author_type'] = author_type

                keyboard = [[InlineKeyboardButton("« Back", callback_data="back_to_filters")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                query.edit_message_text(
                    f"*Enter Author Name* 👤\n\n"
                    f"Type: {author_type.title()}\n"
                    f"Please enter the author name:",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data['awaiting_author'] = True
                return ENTER_AUTHOR

        elif update.message and context.user_data.get('awaiting_author'):
            author = update.message.text.strip()
            if not author:
                update.message.reply_text("❌ Please enter a valid author name")
                return ENTER_AUTHOR

            context.user_data['advanced_filters']['author'] = author
            context.user_data['awaiting_author'] = False

            return show_advanced_search_menu(update, context)

        return CHOOSING_FILTER

    except Exception as e:
        logger.error(f"Error in handle_author_input: {str(e)}")
        message = "❌ An error occurred. Please try again."
        if update.callback_query:
            update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="back_to_filters")
                ]])
            )
        else:
            update.message.reply_text(message)
        return CHOOSING_FILTER

def handle_citations_input(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    logger.info(f"Processing citations input: {query.data}")

    try:
        if query.data.startswith("citations_"):
            citations = int(query.data.split("_")[1])
            context.user_data.setdefault('advanced_filters', {})
            context.user_data['advanced_filters']['min_citations'] = citations
            return show_advanced_search_menu(update, context)

    except Exception as e:
        logger.error(f"Error handling citations input: {str(e)}")
        query.edit_message_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_filters")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )

    return CHOOSING_FILTER

def handle_filter_execute(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer("🔍 Processing your search...")
    logger.info("Executing advanced search with filters")

    try:
        filters = context.user_data.get('advanced_filters', {})
        search_parts = []

        if filters.get('date_from') and filters.get('date_to'):
            date_from = filters['date_from'].replace('-', '')
            date_to = filters['date_to'].replace('-', '')
            search_parts.append(f"submittedDate:[{date_from} TO {date_to}]")

        if filters.get('author'):
            author = filters['author'].strip()
            search_parts.append(f'au:"{author}"')

        if filters.get('min_citations'):
            min_cites = filters['min_citations']
            search_parts.append(f"citations:>={min_cites}")

        if filters.get('categories'):
            cats = ' OR '.join(f"cat:{cat.lower()}" for cat in filters['categories'])
            if cats:
                search_parts.append(f"({cats})")

        if not search_parts:
            query.edit_message_text(
                "❌ Please set at least one filter before searching!\n\n"
                "Use the buttons below to set your search filters.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Back", callback_data="back_to_filters")
                ]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return CHOOSING_FILTER

        search_query = ' AND '.join(search_parts)

        filter_summary = []
        if filters.get('date_from') and filters.get('date_to'):
            filter_summary.append(f"📅 Date: {filters['date_from']} to {filters['date_to']}")
        if filters.get('author'):
            filter_summary.append(f"👤 Author: {filters['author']}")
        if filters.get('min_citations'):
            filter_summary.append(f"📊 Min Citations: {filters['min_citations']}")
        if filters.get('categories'):
            filter_summary.append(f"🔖 Categories: {', '.join(filters['categories'])}")

        query.edit_message_text(
            f"🔍 *Processing Advanced Search*\n\n"
            f"*Active Filters:*\n" + "\n".join(filter_summary) + "\n\n"
            f"Query: `{search_query}`\n\n"
            "Please wait...",
            parse_mode=ParseMode.MARKDOWN
        )

        from arXiv import execute_search

        new_update = Update(update.update_id)
        new_update.message = query.message
        context.user_data['last_search_query'] = search_query
        context.args = [search_query]

        execute_search(new_update, context)

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error executing search: {str(e)}", exc_info=True)
        query.edit_message_text(
            "❌ An error occurred while searching.\n"
            "Please try again or modify your filters.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="back_to_filters")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

def cancel_search(update: Update, context: CallbackContext) -> int:
    try:
        if update.callback_query:
            update.callback_query.edit_message_text(
                "🚫 Search cancelled. Use /search to start a new search."
            )
        else:
            update.message.reply_text(
                "🚫 Search cancelled. Use /search to start a new search."
            )
    except Exception as e:
        logger.error(f"Error canceling search: {str(e)}")
        if update.effective_message:
            update.effective_message.reply_text(
                "❌ An error occurred. Please use /search to start over."
            )

    return ConversationHandler.END