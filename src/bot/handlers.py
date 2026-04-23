import aiohttp
from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.bot.bot import DIRECTOR_QUOTES, DirectorStates
from src.api.config import settings

router = Router()

def get_approval_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="💎 Это шедевр! Снимаем", callback_data="approve_script"),
        types.InlineKeyboardButton(text="🗑 Мусор, переделывай", callback_data="reject_script")
    )
    return builder.as_markup()

def get_scene_keyboard(scene_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"regenerate_scene_{scene_id}"),
        types.InlineKeyboardButton(text="✅ Ок", callback_data=f"approve_scene_{scene_id}")
    )
    return builder.as_markup()

def get_final_render_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🎬 ФИНАЛЬНЫЙ МОНТАЖ", callback_data="start_final_render")
    )
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(DIRECTOR_QUOTES["start"])
    await state.set_state(DirectorStates.AwaitingBrief)

@router.message(DirectorStates.AwaitingBrief)
async def process_brief(message: types.Message, state: FSMContext):
    brief = message.text
    await message.answer(DIRECTOR_QUOTES["brief_received"].format(brief=brief))
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{settings.LOCAL_SERVER_URL}/generate-script"
            payload = {"brief": brief, "user_id": message.from_user.id}
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    await state.update_data(current_script=data)
                    
                    title = data["title"]
                    scenes = data["scenes"]
                    comment = data["director_comment"]
                    
                    response_text = f"📜 **СЦЕНАРИЙ: {title.upper()}**\n\n"
                    for scene in scenes:
                        response_text += f"🎬 *Сцена {scene['scene_id']}*\n"
                        response_text += f"Визуал: {scene['description']}\n"
                        response_text += f"Диалог: _{scene['dialogue']}_\n\n"
                    
                    response_text += f"📽 **Вердикт:** {comment}"
                    
                    await message.answer(DIRECTOR_QUOTES["script_ready"])
                    await message.answer(response_text, parse_mode="Markdown", reply_markup=get_approval_keyboard())
                    await state.set_state(DirectorStates.ScriptApproval)
                else:
                    await message.answer(DIRECTOR_QUOTES["server_error"])
        except Exception as e:
            await message.answer(f"⚠️ Ошибка связи с гаражом: {str(e)}")

@router.callback_query(DirectorStates.ScriptApproval, F.data == "approve_script")
async def approve_script(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Утверждено!")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(DIRECTOR_QUOTES["rendering"])
    
    data = await state.get_data()
    script = data.get("current_script")
    
    if not script:
        await callback.message.answer("Сценарий потерялся в запое. Начни сначала.")
        return

    # Phase 3: Visual Production
    async with aiohttp.ClientSession() as session:
        for scene in script["scenes"]:
            await callback.message.answer(f"🎨 Рисую кадр для сцены {scene['scene_id']}...")
            
            payload = {
                "prompt": scene["image_prompt"],
                "scene_id": scene["scene_id"],
                "user_id": callback.from_user.id
            }
            
            try:
                async with session.post(f"{settings.LOCAL_SERVER_URL}/generate-image", json=payload) as resp:
                    if resp.status == 200:
                        img_data = await resp.json()
                        # Store the image URL in state to use for rendering
                        current_data = await state.get_data()
                        storyboard = current_data.get("storyboard", {})
                        storyboard[str(scene["scene_id"])] = {
                            "image_url": img_data["image_url"],
                            "scene_id": scene["scene_id"],
                            "dialogue": scene["dialogue"]
                        }
                        await state.update_data(storyboard=storyboard)
                        
                        await callback.message.answer_photo(
                            photo=img_data["image_url"],
                            caption=f"🎬 Сцена {scene['scene_id']}\n_{scene['description']}_",
                            parse_mode="Markdown",
                            reply_markup=get_scene_keyboard(scene["scene_id"])
                        )
                    else:
                        await callback.message.answer(f"❌ Не удалось нарисовать сцену {scene['scene_id']}")
            except Exception as e:
                await callback.message.answer(f"⚠️ Ошибка при генерации сцены {scene['scene_id']}: {str(e)}")

    await callback.message.answer("Все кадры готовы. Если всё нравится — жми на кнопку монтажа. Саркастичный инди-фильм сам себя не снимет.", 
                                 reply_markup=get_final_render_keyboard())
    await state.set_state(DirectorStates.StoryboardApproval)

@router.callback_query(F.data.startswith("regenerate_scene_"))
async def regenerate_scene(callback: types.CallbackQuery, state: FSMContext):
    scene_id = int(callback.data.split("_")[-1])
    await callback.answer("Переделываю...")
    
    data = await state.get_data()
    script = data.get("current_script")
    
    scene_data = next((s for s in script["scenes"] if s["scene_id"] == scene_id), None)
    if not scene_data:
        await callback.message.answer("Не нашел данных этой сцены.")
        return

    async with aiohttp.ClientSession() as session:
        payload = {
            "prompt": scene_data["image_prompt"],
            "scene_id": scene_id,
            "user_id": callback.from_user.id
        }
        
        try:
            async with session.post(f"{settings.LOCAL_SERVER_URL}/generate-image", json=payload) as resp:
                if resp.status == 200:
                    img_data = await resp.json()
                    
                    # Update image URL in state
                    current_data = await state.get_data()
                    storyboard = current_data.get("storyboard", {})
                    storyboard[str(scene_id)]["image_url"] = img_data["image_url"]
                    await state.update_data(storyboard=storyboard)

                    await callback.message.answer_photo(
                        photo=img_data["image_url"],
                        caption=f"🔄 Новый вариант: Сцена {scene_id}\n_{scene_data['description']}_",
                        parse_mode="Markdown",
                        reply_markup=get_scene_keyboard(scene_id)
                    )
                else:
                    await callback.message.answer(f"❌ Ошибка при перегенерации.")
        except Exception as e:
            await callback.message.answer(f"⚠️ Ошибка: {str(e)}")

@router.callback_query(F.data.startswith("approve_scene_"))
async def approve_single_scene(callback: types.CallbackQuery):
    await callback.answer("Принято!")
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(DirectorStates.StoryboardApproval, F.data == "start_final_render")
async def start_final_render(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Камера... Мотор!")
    await callback.message.answer("🎥 Начинаю финальный монтаж. Это может занять несколько минут. Сходи пока за кофе, настоящий художник не спешит.")
    
    data = await state.get_data()
    script = data.get("current_script")
    storyboard = data.get("storyboard", {})
    
    # Sort scenes by ID to ensure correct order
    sorted_scenes = []
    for scene_id in sorted([int(sid) for sid in storyboard.keys()]):
        sorted_scenes.append(storyboard[str(scene_id)])
    
    payload = {
        "project_title": script.get("title", "Untitled"),
        "scenes": sorted_scenes,
        "user_id": callback.from_user.id
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{settings.LOCAL_SERVER_URL}/start-render"
            async with session.post(url, json=payload, timeout=600) as resp:
                if resp.status == 200:
                    render_data = await resp.json()
                    video_url = render_data["video_url"]
                    
                    await callback.message.answer("🎉 Твой фильм готов! Смотри, пока критики не разнесли.")
                    await callback.message.answer_video(
                        video=video_url,
                        caption=f"🎬 **{script.get('title', 'Movie').upper()}**\n\nСнято в Гараже.",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                else:
                    err = await resp.json()
                    await callback.message.answer(f"❌ Монтажер упал в обморок: {err.get('detail', 'Unknown error')}")
        except Exception as e:
            await callback.message.answer(f"⚠️ Ошибка связи при монтаже: {str(e)}")

@router.callback_query(DirectorStates.ScriptApproval, F.data == "reject_script")
async def reject_script(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("В корзину!")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Ладно, ладно. Напиши еще раз, чего ты хочешь, только в этот раз постарайся.")
    await state.set_state(DirectorStates.AwaitingBrief)

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(DIRECTOR_QUOTES["help"])
