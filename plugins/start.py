# Code modified and maintained by @EithonX
# For support or inquiries related to these modifications, contact @EithonX or @Film_Bee.
#
# Copyright (C) for these modifications 2025 by EithonX <https://t.me/EithonX>.
#
# This file is part of the @Film_Bee bot project by @EithonX.
# (If this is a derivative of an open-source project, please ensure you
# respect the original license terms. Original license details may have been altered or removed.)
#
# All rights reserved.
#

import asyncio
import os
import random
import sys
import re
import string
import string as rohit # Left as is, per instruction not to change functional code
import time
from datetime import datetime, timedelta
from pytz import timezone # Import for timezone
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant

# Assuming Bot, config, helper_func, database, and db_premium are correctly set up by you
from bot import Bot
from config import * # BAN_SUPPORT, TUT_VID, SHORTLINK_URL, etc. will be taken from your modified config
from helper_func import *
from database.database import *
from database.db_premium import * # Includes collection, is_premium_user, add_premium, remove_premium, check_user_plan etc.


# These will use the values from your modified config.py
BAN_SUPPORT_LINK = f"{BAN_SUPPORT}" # Renamed to avoid conflict if BAN_SUPPORT is also a direct string
TUT_VID_LINK = f"{TUT_VID}" # Renamed to avoid conflict if TUT_VID is also a direct string

async def short_url(client: Client, message: Message, base64_string):
    try:
        prem_link = f"https://t.me/{client.username}?start=yu3elk{base64_string}7"
        # SHORTLINK_URL and SHORTLINK_API are from your config
        short_link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, prem_link)

        buttons = [
            [
                InlineKeyboardButton(text="ᴅᴏᴡɴʟᴏᴀᴅ", url=short_link),
                InlineKeyboardButton(text="ᴛᴜᴛᴏʀɪᴀʟ", url=TUT_VID_LINK) # MODIFIED to use renamed variable
            ],
            [
                InlineKeyboardButton(text="ᴘʀᴇᴍɪᴜᴍ", callback_data="premium")
            ]
        ]
        # SHORTENER_PIC and SHORT_MSG are from your config
        await message.reply_photo(
            photo=SHORTENER_PIC,
            caption=SHORT_MSG.format(
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except IndexError:
        pass
    except Exception as e: # Added general exception catch for short_url
        print(f"Error in short_url: {e}")


@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    # id = message.from_user.id # This 'id' is the same as user_id, can be removed if not used distinctively
    is_premium = await is_premium_user(user_id) # Use user_id consistently

    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>⛔️ You are Bᴀɴɴᴇᴅ from using this bot.</b>\n\n"
            "<i>Contact support if you think this is a mistake.</i>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT_LINK)]] # MODIFIED to use renamed variable
            )
        )

    # ✅ Check Force Subscription
    # is_subscribed and not_joined are from helper_func.py (modified in previous steps)
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    # File auto-delete time in seconds
    FILE_AUTO_DELETE = await db.get_del_timer()

    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except:
            pass

    # Handle normal message flow
    text = message.text

    if len(text) > 7 and text.startswith("/start "): # Ensure it's a deep link
        try:
            basic = text.split(" ", 1)[1]
            if basic.startswith("yu3elk"):
                base64_string = basic[6:-1]
            else:
                base64_string = basic

            if not is_premium and user_id != OWNER_ID and not basic.startswith("yu3elk"):
                await short_url(client, message, base64_string)
                return

        except Exception as e:
            print(f"Error processing start payload: {e}")
            # Fall through to normal start message if payload processing fails for deep link
            # Or handle error specifically: await message.reply_text("Invalid link format.") return

        # Ensure base64_string is defined before proceeding
        if 'base64_string' not in locals():
             # This means the deep link was malformed or not a file link type
             pass # Will fall through to the generic start message
        else:
            try:
                string_decoded = await decode(base64_string) # decode is from helper_func.py
                argument = string_decoded.split("-")
            except Exception as e:
                print(f"Error decoding base64 string: {e}. String was: {base64_string}")
                # Fall through or reply with error: await message.reply_text("Invalid link.") return

            ids = []
            if 'argument' in locals() and len(argument) == 3:
                try:
                    start_id = int(int(argument[1]) / abs(client.db_channel.id))
                    end_id = int(int(argument[2]) / abs(client.db_channel.id))
                    ids = range(start_id, end_id + 1) if start_id <= end_id else list(range(start_id, end_id - 1, -1))
                except Exception as e:
                    print(f"Error decoding range IDs: {e}")
                    # Fall through or reply: await message.reply_text("Error processing link (range).") return

            elif 'argument' in locals() and len(argument) == 2:
                try:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                except Exception as e:
                    print(f"Error decoding single ID: {e}")
                    # Fall through or reply: await message.reply_text("Error processing link (single).") return
            
            if not ids: # If ids list is empty due to errors or invalid format, don't proceed with file sending
                # Fall through to generic start message or show error
                pass
            else:
                temp_msg = await message.reply("<b>Please wait...</b>")
                try:
                    # get_messages is from helper_func.py
                    messages_to_send = await get_messages(client, ids)
                except Exception as e:
                    await message.reply_text("Something went wrong fetching files!")
                    print(f"Error getting messages: {e}")
                    await temp_msg.delete()
                    return
                finally:
                    if temp_msg: await temp_msg.delete()


                # Internal variable name 'codeflix_msgs' is kept as is.
                sent_messages_list = [] # Renamed for clarity, was codeflix_msgs

                for msg_to_copy in messages_to_send:
                    original_caption = msg_to_copy.caption.html if msg_to_copy.caption else ""
                    # CUSTOM_CAPTION is from your config
                    caption = f"{original_caption}\n\n{CUSTOM_CAPTION}" if CUSTOM_CAPTION else original_caption
                    # DISABLE_CHANNEL_BUTTON is from your config
                    reply_markup = msg_to_copy.reply_markup if DISABLE_CHANNEL_BUTTON else None

                    try:
                        snt_msg = await msg_to_copy.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT # PROTECT_CONTENT from your config
                        )
                        await asyncio.sleep(0.5)
                        sent_messages_list.append(snt_msg)
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        copied_msg = await msg_to_copy.copy(
                            chat_id=message.from_user.id,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                            protect_content=PROTECT_CONTENT
                        )
                        sent_messages_list.append(copied_msg)
                    except Exception as e_copy:
                        print(f"Error copying message {msg_to_copy.id}: {e_copy}")
                        pass

                if FILE_AUTO_DELETE > 0 and sent_messages_list:
                    notification_msg = await message.reply(
                        f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</b>"
                    )

                    await asyncio.sleep(FILE_AUTO_DELETE)

                    for snt_msg_to_delete in sent_messages_list:
                        if snt_msg_to_delete:
                            try:
                                await snt_msg_to_delete.delete()
                            except Exception as e_del:
                                print(f"Error deleting message {snt_msg_to_delete.id}: {e_del}")

                    try:
                        reload_url = (
                            f"https://t.me/{client.username}?start={text.split(' ', 1)[1]}"
                            if text.startswith("/start ") and len(text.split(" ", 1)) > 1
                            else None
                        )
                        keyboard = InlineKeyboardMarkup(
                            [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                        ) if reload_url else None

                        await notification_msg.edit(
                            "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                            reply_markup=keyboard
                        )
                    except Exception as e_notify_edit:
                        print(f"Error updating notification with 'Get File Again' button: {e_notify_edit}")
                return # Successfully processed deep link or auto-deleted files

    # This part executes if not a deep link, or if deep link processing falls through without returning
    reply_markup_start = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("• ᴏᴜʀ ᴄʜᴀɴɴᴇʟ •", url="https://t.me/Film_Bee")], # MODIFIED link
            [
                InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
                InlineKeyboardButton('ʜᴇʟᴘ •', callback_data="help")
            ]
        ]
    )
    # START_PIC and START_MSG are from your config
    await message.reply_photo(
        photo=START_PIC,
        caption=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup_start,
        # message_effect_id=5104841245755180586 # 🔥 # This might require specific client versions or bot permissions
    )
    return

#=====================================================================================##
# Modified by @EithonX. Contact @EithonX or @Film_Bee for support.
#=====================================================================================##

# Create a global dictionary to store chat data (cache)
chat_data_cache = {}

async def not_joined(client: Client, message: Message):
    temp = await message.reply("<b><i>Checking Subscription... Please wait.</i></b>")
    user_id = message.from_user.id
    buttons = []
    count = 0 # For visual feedback if needed, like "!!!"

    try:
        all_channels_from_db = await db.show_channels() # Should return list of chat_ids
        if not all_channels_from_db: # If no channels are set for fsub
            await temp.delete() # No need for the "Checking..." message
            return # Or, you might want to call the original handler again if logic allows

        for chat_id in all_channels_from_db:
            mode = await db.get_channel_mode(chat_id) # fetch mode
            await message.reply_chat_action(ChatAction.TYPING)

            if not await is_sub(client, user_id, chat_id): # is_sub is from helper_func
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data
                    
                    name = data.title
                    link = "" # Initialize link

                    if mode == "on" and not data.username: # Private channel with approval mode
                        invite_details = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY > 0 else None
                        )
                        link = invite_details.invite_link
                    else: # Public channel or private channel without approval mode (direct join)
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else: # Private channel, generate normal invite link
                            invite_details = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY > 0 else None
                            )
                            link = invite_details.invite_link
                    
                    buttons.append([InlineKeyboardButton(text=name, url=link)])
                    count += 1
                    # await temp.edit(f"<b>{'! ' * count}Please join the channel(s) below.</b>") # Optional: update temp message

                except Exception as e_chat:
                    print(f"Error processing channel {chat_id} for fsub: {e_chat}")
                    # MODIFIED: Developer contact updated
                    await temp.edit(
                        f"<b><i>! Eʀʀᴏʀ with one of the required channels. Please Cᴏɴᴛᴀᴄᴛ @EithonX</i></b>\n"
                        f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> Problem fetching details for a required channel.</blockquote>"
                    )
                    return # Stop if one channel has an issue

        if not buttons: # User is subscribed to all, or no channels were problematic
            await temp.delete()
            return # Let the original command handler continue (though this function is typically called when is_subscribed is False)

        # Retry Button
        try:
            # Ensure message.command is not None and has enough elements
            if message.command and len(message.command) > 1:
                 start_payload = message.command[1]
                 buttons.append([
                    InlineKeyboardButton(
                        text='♻️ Tʀʏ Aɢᴀɪɴ',
                        url=f"https://t.me/{client.username}?start={start_payload}"
                    )
                ])
            else: # Fallback if no deep link payload
                 buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', url=f"https://t.me/{client.username}")])

        except IndexError: # Should be caught by the check above now
            buttons.append([InlineKeyboardButton(text='♻️ Tʀʏ Aɢᴀɪɴ', url=f"https://t.me/{client.username}")])
            pass
        
        await temp.delete() # Delete "Checking..." message before sending the photo

        # FORCE_PIC and FORCE_MSG are from your config
        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e_fsub_main:
        print(f"Major Error in not_joined (ForceSubscribe logic): {e_fsub_main}")
        # MODIFIED: Developer contact updated
        await temp.edit(
            f"<b><i>! Eʀʀᴏʀ in subscription check. Please Cᴏɴᴛᴀᴄᴛ @EithonX</i></b>\n"
            f"<blockquote expandable><b>Rᴇᴀsᴏɴ:</b> {e_fsub_main}</blockquote>"
        )

#=====================================================================================##

@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id
    status_message = await check_user_plan(user_id) # from db_premium
    await message.reply(status_message)

#=====================================================================================##
# Command to add premium user
@Bot.on_message(filters.command('addpremium') & filters.private & admin) # admin filter from helper_func
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text(
            "Usage: /addpremium <user_id> <time_value> <time_unit>\n\n"
            "Time Units:\n"
            "s - seconds\n"
            "m - minutes\n"
            "h - hours\n"
            "d - days\n"
            "y - years\n\n"
            "Examples:\n"
            "/addpremium 123456789 30 m → 30 minutes\n"
            "/addpremium 123456789 2 h → 2 hours\n"
            "/addpremium 123456789 1 d → 1 day\n"
            "/addpremium 123456789 1 y → 1 year"
        )
        return

    try:
        user_id_to_add = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()

        expiration_time = await add_premium(user_id_to_add, time_value, time_unit) # from db_premium

        await msg.reply_text(
            f"✅ User `{user_id_to_add}` added as a premium user for {time_value} {time_unit}.\n"
            f"Expiration Time: `{expiration_time}`"
        )

        await client.send_message(
            chat_id=user_id_to_add,
            text=(
                f"🎉 Premium Activated!\n\n"
                f"You have received premium access for `{time_value} {time_unit}`.\n"
                f"Expires on: `{expiration_time}`"
            ),
        )
    except ValueError:
        await msg.reply_text("❌ Invalid input. Please ensure user ID and time value are numbers.")
    except Exception as e:
        await msg.reply_text(f"⚠️ An error occurred: `{str(e)}`")

# Command to remove premium user
@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("Usage: /remove_premium <user_id>")
        return
    try:
        user_id_to_remove = int(msg.command[1])
        await remove_premium(user_id_to_remove) # from db_premium
        await msg.reply_text(f"User {user_id_to_remove} has been removed from premium.")
    except ValueError:
        await msg.reply_text("User ID must be an integer.")
    except Exception as e: # Catch if user not found or other db errors
        await msg.reply_text(f"Could not remove premium: {e}")


# Command to list active premium users
@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client, message):
    ist = timezone("Asia/Kolkata") # Ensure pytz is installed: pip install pytz
    premium_users_cursor = collection.find({}) # collection from db_premium
    premium_user_list = ['<b>Active Premium Users:</b>']
    current_time_ist = datetime.now(ist)
    found_active = False

    async for user_doc in premium_users_cursor:
        user_id_premium = user_doc["user_id"]
        expiration_timestamp_str = user_doc["expiration_timestamp"]

        try:
            expiration_time_utc = datetime.fromisoformat(expiration_timestamp_str)
            if expiration_time_utc.tzinfo is None: # If no timezone, assume UTC
                 expiration_time_utc = timezone('UTC').localize(expiration_time_utc)
            expiration_time_ist = expiration_time_utc.astimezone(ist)

            remaining_time = expiration_time_ist - current_time_ist

            if remaining_time.total_seconds() <= 0:
                await collection.delete_one({"user_id": user_id_premium})
                continue
            
            found_active = True
            user_info = await client.get_users(user_id_premium)
            username = f"@{user_info.username}" if user_info.username else "N/A"
            # first_name = user_info.first_name # Not used in current format string
            mention = user_info.mention

            days = remaining_time.days
            hours, remainder_seconds = divmod(remaining_time.seconds, 3600)
            minutes, seconds = divmod(remainder_seconds, 60)
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            premium_user_list.append(
                f"<b>User:</b> {mention} ({username})\n"
                f"<b>ID:</b> <code>{user_id_premium}</code>\n"
                f"<b>Expires in:</b> {expiry_info}"
            )
        except Exception as e_list_prem:
            premium_user_list.append(
                f"UserID: <code>{user_id_premium}</code>\n"
                f"Error fetching details: ({str(e_list_prem)})"
            )

    if not found_active:
        await message.reply_text("I found 0 active premium users in my DB.")
    else:
        # Split message if too long
        final_message = ""
        for item in premium_user_list:
            if len(final_message) + len(item) + 2 > 4096: # 2 for \n\n
                await message.reply_text(final_message, parse_mode=ParseMode.HTML)
                final_message = item
            else:
                if final_message: # Add separator if not the first item (header)
                    final_message += f"\n\n{item}"
                else: # For the header "Active Premium Users:"
                    final_message = item
        if final_message: # Send the last part
            await message.reply_text(final_message, parse_mode=ParseMode.HTML)

#=====================================================================================##

@Bot.on_message(filters.command("count") & filters.private & admin)
async def total_verify_count_cmd(client, message: Message):
    total = await db.get_total_verify_count()
    await message.reply_text(f"Tᴏᴛᴀʟ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴋᴇɴs ᴛᴏᴅᴀʏ: <b>{total}</b>")

#=====================================================================================##

@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data = "close")]])
    # CMD_TXT is from your config.py (already modified in the first script)
    await message.reply(text=CMD_TXT, reply_markup = reply_markup, quote= True)
