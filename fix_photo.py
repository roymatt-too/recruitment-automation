"""Fix agentic_photo to save images as files and use Read tool."""
import re

with open("src/bot/orchestrator.py", "r") as f:
    lines = f.readlines()

# Find the start and end of agentic_photo method
start_line = None
end_line = None
for i, line in enumerate(lines):
    if "async def agentic_photo(" in line:
        start_line = i
    elif start_line is not None and line.strip().startswith("async def agentic_repo("):
        end_line = i
        break

if start_line is None or end_line is None:
    print(f"ERROR: Could not find method boundaries (start={start_line}, end={end_line})")
    exit(1)

print(f"Found agentic_photo at lines {start_line+1}-{end_line}")

new_method = '''    async def agentic_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Process photo -> Claude by saving to file and using Read tool."""
        import os as _os

        user_id = update.effective_user.id

        chat = update.message.chat
        await chat.send_action("typing")
        progress_msg = await update.message.reply_text("Working...")

        try:
            # Download image from Telegram and save to file
            photo = update.message.photo[-1]
            tg_file = await photo.get_file()

            img_dir = "/root/.telegram_images"
            _os.makedirs(img_dir, exist_ok=True)

            ext = ".jpg"
            if tg_file.file_path:
                if tg_file.file_path.endswith(".png"):
                    ext = ".png"
                elif tg_file.file_path.endswith(".webp"):
                    ext = ".webp"

            img_path = _os.path.join(
                img_dir, f"img_{user_id}_{int(time.time())}{ext}"
            )
            await tg_file.download_to_drive(img_path)

            # Build prompt that tells Claude to read the image file
            caption = update.message.caption or ""
            if caption:
                prompt = (
                    f"Use the Read tool to view this image file: {img_path}\\n\\n"
                    f"User request: {caption}"
                )
            else:
                prompt = (
                    f"Use the Read tool to view this image file: {img_path}\\n\\n"
                    f"Describe what you see and provide any relevant analysis."
                )

            claude_integration = context.bot_data.get("claude_integration")
            if not claude_integration:
                await progress_msg.edit_text(
                    "Claude integration not available. Check configuration."
                )
                return

            current_dir = context.user_data.get(
                "current_directory", self.settings.approved_directory
            )
            session_id = context.user_data.get("claude_session_id")

            force_new = bool(context.user_data.get("force_new_session"))

            verbose_level = self._get_verbose_level(context)
            tool_log: List[Dict[str, Any]] = []
            on_stream = self._make_stream_callback(
                verbose_level, progress_msg, tool_log, time.time()
            )

            heartbeat = self._start_typing_heartbeat(chat)
            try:
                claude_response = await claude_integration.run_command(
                    prompt=prompt,
                    working_directory=current_dir,
                    user_id=user_id,
                    session_id=session_id,
                    on_stream=on_stream,
                    force_new=force_new,
                )
            finally:
                heartbeat.cancel()

            if force_new:
                context.user_data["force_new_session"] = False

            context.user_data["claude_session_id"] = claude_response.session_id

            from .utils.formatting import ResponseFormatter

            formatter = ResponseFormatter(self.settings)
            formatted_messages = formatter.format_claude_response(
                claude_response.content
            )

            await progress_msg.delete()

            for i, message in enumerate(formatted_messages):
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=None,
                    reply_to_message_id=(update.message.message_id if i == 0 else None),
                )
                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

            # Clean up image file after processing
            try:
                _os.remove(img_path)
            except OSError:
                pass

        except Exception as e:
            from .handlers.message import _format_error_message

            await progress_msg.edit_text(_format_error_message(e), parse_mode="HTML")
            logger.error(
                "Claude photo processing failed", error=str(e), user_id=user_id
            )

'''

# Replace the method
new_lines = lines[:start_line] + [new_method] + lines[end_line:]

with open("src/bot/orchestrator.py", "w") as f:
    f.writelines(new_lines)

print("SUCCESS: agentic_photo replaced with file-based image reading")
