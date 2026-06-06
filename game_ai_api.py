"""
Game AI - API版本
使用外部大模型API进行游戏操作，本地OCR（pytesseract）识别屏幕文字。
支持经验总结与复用。
"""

import json
import time
import re
import sys
import os
import base64
import warnings
from pathlib import Path
from dataclasses import dataclass, asdict

warnings.filterwarnings("ignore")

# ============================================================
#  结构化输出定义
# ============================================================

@dataclass
class GameAction:
    """模型输出的标准动作格式"""
    action: str          # move / click / attack / use_item / wait / explore / custom
    target: str = ""     # enemy / door / npc / item
    direction: str = ""  # up / down / left / right
    position: str = ""   # x,y
    confidence: float = 0.0
    reasoning: str = ""
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Experience:
    """经验记录"""
    id: int = 0
    timestamp: str = ""
    observation: str = ""
    action: str = ""
    result: str = ""
    lesson: str = ""


# ============================================================
#  简单本地 OCR（基于 pytesseract / easyocr fallback）
# ============================================================

class LocalOCR:
    """本地OCR：优先pytesseract，fallback到easyocr，都没有则提示"""

    def __init__(self, lang: str = "chi_sim+eng"):
        self.lang = lang
        self._backend = None
        self._engine = None

        # 尝试 pytesseract
        try:
            import pytesseract
            from PIL import Image
            self._engine = pytesseract
            self._Image = Image
            self._backend = "pytesseract"
            print("[OCR] pytesseract 加载成功")
            return
        except ImportError:
            pass

        # 尝试 easyocr
        try:
            import easyocr
            langs = ["ch_sim", "en"] if "chi" in lang else ["en"]
            self._engine = easyocr.Reader(langs, gpu=False)
            self._backend = "easyocr"
            print("[OCR] easyocr 加载成功")
            return
        except ImportError:
            pass

        print("[OCR] 警告: 无可用OCR引擎。请安装: pip install pytesseract Pillow 或 pip install easyocr")

    def recognize(self, image_path: str = None, image_bytes: bytes = None) -> str:
        if not self._backend:
            return "[OCR不可用] 请安装 pytesseract 或 easyocr"
        try:
            import io
            if self._backend == "pytesseract":
                if image_bytes:
                    img = self._Image.open(io.BytesIO(image_bytes))
                elif image_path:
                    img = self._Image.open(image_path)
                else:
                    return "[未提供图片]"
                return self._engine.image_to_string(img, lang=self.lang).strip()
            elif self._backend == "easyocr":
                if image_bytes:
                    img_bytes = image_bytes
                elif image_path:
                    with open(image_path, "rb") as f:
                        img_bytes = f.read()
                else:
                    return "[未提供图片]"
                result = self._engine.readtext(img_bytes)
                return "\n".join([r[1] for r in result])
        except Exception as e:
            return f"[OCR错误] {e}"
        return ""

    @property
    def is_available(self) -> bool:
        return self._backend is not None


# ============================================================
#  经验管理器
# ============================================================

class ExperienceManager:
    def __init__(self, filepath: str = "experiences_api.json"):
        self.filepath = Path(filepath)
        self.experiences: list[Experience] = []
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                data = json.loads(self.filepath.read_text(encoding="utf-8"))
                self.experiences = [Experience(**e) for e in data]
                print(f"[经验] 已加载 {len(self.experiences)} 条经验")
            except Exception:
                self.experiences = []

    def save(self):
        data = [asdict(e) for e in self.experiences]
        self.filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, observation: str, action: str, result: str, lesson: str = ""):
        exp = Experience(
            id=len(self.experiences) + 1,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            observation=observation, action=action,
            result=result, lesson=lesson,
        )
        self.experiences.append(exp)
        self.save()

    def get_recent(self, n: int = 5) -> str:
        if not self.experiences:
            return ""
        recent = self.experiences[-n:]
        lines = []
        for e in recent:
            lines.append(
                f"#{e.id} [{e.timestamp}]\n"
                f"  观察: {e.observation[:200]}\n"
                f"  动作: {e.action[:200]}\n"
                f"  结果: {e.result[:200]}\n"
                f"  经验: {e.lesson[:200]}"
            )
        return "\n---\n".join(lines)

    def get_summary(self) -> str:
        lessons = [e.lesson for e in self.experiences if e.lesson]
        if not lessons:
            return "暂无经验总结"
        return "\n".join(f"- {l}" for l in lessons[-20:])


# ============================================================
#  游戏AI（API版）
# ============================================================

class GameAI_API:
    OUTPUT_SCHEMA = """{
    "actions": [
        {
            "type": "操作类型",
            "key": "按键名",
            "keys": ["组合按键"],
            "position": "x,y",
            "direction": "方向",
            "duration": "持续时间(毫秒)"
        }
    ],
    "confidence": "0~1",
    "reasoning": "推理过程",
    "goal_achieved": false,
    "progress": "当前进度描述"
}"""

    ACTION_TYPES = """
实际游戏按键操作类型：

1. key_press: 单键按下
   - key: 按键名 (如 w/a/s/d, space, enter, esc, tab, shift, ctrl, alt, 1-9, f1-f12)
   - 示例: {"type": "key_press", "key": "space"}

2. key_combo: 组合键
   - keys: 按键数组 (先按住前面的键，再按最后一个)
   - 示例: {"type": "key_combo", "keys": ["shift", "w"]} 表示 Shift+W

3. key_hold: 长按按键
   - key: 按键名
   - duration: 持续时间(毫秒)
   - 示例: {"type": "key_hold", "key": "w", "duration": 1000}

4. mouse_click: 鼠标点击
   - position: "x,y" 屏幕坐标
   - button: "left" / "right" / "middle"
   - 示例: {"type": "mouse_click", "position": "500,300", "button": "left"}

5. mouse_double_click: 鼠标双击
   - position: "x,y"
   - 示例: {"type": "mouse_double_click", "position": "500,300"}

6. mouse_move: 鼠标移动
   - position: "x,y"
   - 示例: {"type": "mouse_move", "position": "500,300"}

7. mouse_drag: 鼠标拖拽
   - start: "x,y" 起点
   - end: "x,y" 终点
   - 示例: {"type": "mouse_drag", "start": "100,100", "end": "500,500"}

8. scroll: 滚轮
   - direction: "up" / "down"
   - amount: 滚动量
   - 示例: {"type": "scroll", "direction": "down", "amount": 3}

常见游戏动作参考（请用实际按键实现）：
- 移动: W/A/S/D
- 跳跃: space
- 攻击/射击: 鼠标左键 或 J
- 技能: Q/E/R/F 或 1-4
- 交互/拾取: E 或 F
- 打开背包: I 或 Tab
- 打开地图: M
- 菜单: Esc
- 奔跑: Shift+W
- 蹲下: Ctrl 或 C
"""

    SYSTEM_PROMPT = f"""你是一个游戏AI助手。根据游戏屏幕截图的OCR识别结果做出操作决策。

{ACTION_TYPES}

必须严格以JSON格式输出：
{OUTPUT_SCHEMA}

规则：
1. 使用实际游戏按键，不要使用抽象概念如"攻击"、"使用物品"
2. 可以输出一连串按键动作，AI会按顺序执行
3. 根据OCR识别的游戏状态判断应该按什么键
4. reasoning字段说明判断依据
5. confidence反映把握程度
6. goal_achieved标记目标是否已完成
7. progress描述当前进度"""

    def __init__(self, api_key: str, base_url: str = "https://gvmz.systems/v1",
                 model: str = "gpt-5.4-mini", experience_file: str = "experiences_api.json"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.ocr = LocalOCR()
        self.experience = ExperienceManager(experience_file)
        self.history: list[dict] = []
        print(f"[GameAI-API] 模型: {model}, OCR: {'可用' if self.ocr.is_available else '不可用'}")

    def _call_api_stream(self, messages: list, max_tokens: int = 512, retries: int = 3, timeout: int = 300) -> str:
        """使用requests直接发送流式API请求，带重试"""
        import requests as req
        last_error = None
        
        for attempt in range(retries):
            try:
                print(f"  [API请求] 第{attempt+1}次尝试...")
                resp = req.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": max_tokens,
                        "stream": True,
                    },
                    timeout=timeout,
                    stream=True,
                )
                resp.raise_for_status()
                
                result = ""
                chunk_count = 0
                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8")
                    if not decoded.startswith("data: ") or decoded == "data: [DONE]":
                        continue
                    try:
                        chunk = json.loads(decoded[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        result += delta
                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            print(f"  [API请求] 已接收 {chunk_count} 个数据块...")
                    except (json.JSONDecodeError, IndexError, KeyError):
                        pass
                
                print(f"  [API请求] 完成，共接收 {chunk_count} 个数据块")
                if result.strip():
                    return result.strip()
                else:
                    print(f"  [API请求] 警告: 返回空内容")
                    
            except req.Timeout as e:
                last_error = e
                print(f"  [重试] 第{attempt+1}次超时: {timeout}秒")
                if attempt < retries - 1:
                    print(f"  [重试] 等待5秒后重试...")
                    time.sleep(5)
            except req.ConnectionError as e:
                last_error = e
                print(f"  [重试] 第{attempt+1}次连接错误: {e}")
                if attempt < retries - 1:
                    print(f"  [重试] 等待5秒后重试...")
                    time.sleep(5)
            except Exception as e:
                last_error = e
                print(f"  [重试] 第{attempt+1}次失败: {e}")
                if attempt < retries - 1:
                    print(f"  [重试] 等待5秒后重试...")
                    time.sleep(5)
        
        raise last_error if last_error else Exception("API请求失败，无响应内容")

    def get_action(self, game_state_text: str = "", image_path: str = None, image_bytes: bytes = None) -> GameAction:
        ocr_text = ""
        if image_path or image_bytes:
            ocr_text = self.ocr.recognize(image_path=image_path, image_bytes=image_bytes)

        parts = []
        if ocr_text:
            parts.append(f"[屏幕文字(OCR识别)]\n{ocr_text}")
        if game_state_text:
            parts.append(f"[游戏状态描述]\n{game_state_text}")

        exp_context = self.experience.get_recent(5)
        if exp_context:
            parts.append(f"[历史经验参考]\n{exp_context}")

        user_msg = "\n\n".join(parts) if parts else "请根据当前情况做出游戏操作决策。"

        try:
            raw = self._call_api_stream([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ])
        except Exception as e:
            return GameAction(action="wait", reasoning=f"API调用失败: {e}", raw_text="")

        action = self._parse_action(raw)
        self.history.append({"observation": user_msg[:500], "action": action.to_dict()})
        return action

    def summarize_experience(self) -> str:
        if not self.history:
            return "本次会话无动作记录，无需总结。"

        history_text = json.dumps(self.history, ensure_ascii=False, indent=2)
        prompt = (
            f"以下是本次游戏会话的所有观察和动作记录：\n\n{history_text}\n\n"
            "请总结出3~5条关键经验教训，帮助未来做出更好的决策。"
            "每条经验用一句话概括，直接输出经验列表，不要多余内容。"
            "输出格式：每行一条，以 - 开头。"
        )

        try:
            summary = self._call_api_stream([
                {"role": "system", "content": "你是游戏策略分析专家，擅长从行动记录中提炼经验。"},
                {"role": "user", "content": prompt},
            ], max_tokens=1024)
        except Exception as e:
            summary = f"总结失败: {e}"

        for h in self.history:
            action_dict = h.get("action", {})
            self.experience.add(
                observation=h.get("observation", "")[:500],
                action=json.dumps(action_dict, ensure_ascii=False),
                result=action_dict.get("reasoning", ""),
                lesson=summary,
            )
        self.history.clear()
        return summary

    GOAL_SYSTEM_PROMPT = f"""你是一个游戏AI助手，正在帮助玩家完成一个目标。
你将收到：
1. 当前目标
2. OCR识别的游戏屏幕文字
3. 历史动作记录

{ACTION_TYPES}

你需要：
1. 分析OCR识别的游戏状态
2. 判断应该按什么键来完成目标
3. 输出实际的按键操作序列

必须严格以JSON格式输出：
{OUTPUT_SCHEMA}

规则：
1. 使用实际按键，如 W/A/S/D、space、鼠标点击等
2. 不要使用抽象概念如"攻击"、"使用物品"
3. 根据游戏画面判断应该按什么键
4. 可以输出多个按键动作形成连招
5. reasoning说明为什么按这些键
6. goal_achieved标记目标是否完成"""

    def get_action_for_goal(self, goal: str, game_state_text: str = "", 
                           step_history: list = None, image_path: str = None, 
                           image_bytes: bytes = None,
                           screenshot_func=None) -> GameAction:
        """目标驱动的决策 - 每次都进行OCR识别"""
        
        # 每次都尝试获取屏幕截图并进行OCR识别
        ocr_text = ""
        try:
            if screenshot_func:
                # 调用截图函数获取当前屏幕
                screenshot = screenshot_func()
                if screenshot:
                    ocr_text = self.ocr.recognize(image_bytes=screenshot)
                    print(f"  [OCR] 识别结果: {ocr_text[:200]}...")
            elif image_path or image_bytes:
                ocr_text = self.ocr.recognize(image_path=image_path, image_bytes=image_bytes)
        except Exception as e:
            print(f"  [OCR] 识别失败: {e}")

        parts = [f"[当前目标]\n{goal}"]
        
        # 优先使用OCR识别结果
        if ocr_text:
            parts.append(f"[OCR识别的游戏画面]\n{ocr_text}")
        elif game_state_text:
            parts.append(f"[游戏状态描述]\n{game_state_text}")
        else:
            parts.append("[游戏状态]\n无法获取游戏画面，请等待截图功能可用")
        
        if step_history:
            history_text = "\n".join([f"步骤{i+1}: {h}" for i, h in enumerate(step_history[-5:])])
            parts.append(f"[已执行步骤]\n{history_text}")

        exp_context = self.experience.get_recent(5)
        if exp_context:
            parts.append(f"[历史经验参考]\n{exp_context}")

        user_msg = "\n\n".join(parts)

        try:
            raw = self._call_api_stream([
                {"role": "system", "content": self.GOAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ])
        except Exception as e:
            return GameAction(action="key_press", reasoning=f"API调用失败: {e}", raw_text="")

        action = self._parse_action_with_goal(raw)
        self.history.append({"observation": user_msg[:500], "action": action.to_dict()})
        return action

    def _parse_action_with_goal(self, raw: str) -> GameAction:
        """解析包含多个动作和goal_achieved字段的响应"""
        json_str = raw
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                json_str = raw[start:end + 1]
        try:
            data = json.loads(json_str)
            
            # 支持新的多动作格式
            actions = data.get("actions", [])
            if not actions:
                # 兼容旧格式：单个动作
                single_action = {
                    "type": data.get("action", "wait"),
                    "target": data.get("target", ""),
                    "direction": data.get("direction", ""),
                    "position": data.get("position", ""),
                    "key": data.get("key", ""),
                    "duration": data.get("duration", 0)
                }
                actions = [single_action]
            
            # 将多个动作序列化为字符串
            actions_str = json.dumps(actions, ensure_ascii=False)
            
            # 使用第一个动作作为主动作
            first_action = actions[0] if actions else {}
            
            action = GameAction(
                action=first_action.get("type", "wait"),
                target=first_action.get("target", ""),
                direction=first_action.get("direction", ""),
                position=first_action.get("position", ""),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                raw_text=raw,
            )
            # 添加目标相关字段和动作序列
            action.__dict__['goal_achieved'] = data.get('goal_achieved', False)
            action.__dict__['progress'] = data.get('progress', '')
            action.__dict__['actions'] = actions  # 动作列表
            action.__dict__['actions_str'] = actions_str  # 动作序列字符串
            return action
        except (json.JSONDecodeError, ValueError):
            return GameAction(action="wait", reasoning="输出解析失败", raw_text=raw)

    @staticmethod
    def _parse_action(raw: str) -> GameAction:
        json_str = raw
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                json_str = raw[start:end + 1]
        try:
            data = json.loads(json_str)
            return GameAction(
                action=data.get("action", "wait"),
                target=data.get("target", ""),
                direction=data.get("direction", ""),
                position=data.get("position", ""),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                raw_text=raw,
            )
        except (json.JSONDecodeError, ValueError):
            return GameAction(action="wait", reasoning="输出解析失败", raw_text=raw)


# ============================================================
#  主程序入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Game AI - API版本")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""), help="API Key")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", "https://gvmz.systems/v1"), help="API Base URL")
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME", "gpt-5.4-mini"), help="API模型名")
    args = parser.parse_args()

    print("=" * 50)
    print("  Game AI - API版本")
    print("=" * 50)

    if not args.api_key:
        print("[错误] 请通过 --api-key 或环境变量 OPENAI_API_KEY 设置API密钥")
        print("示例: python game_ai_api.py --api-key sk-xxx --base-url https://api.openai.com/v1")
        sys.exit(1)

    ai = GameAI_API(api_key=args.api_key, base_url=args.base_url, model=args.model)

    # 模拟游戏循环
    print("\n[演示] 模拟游戏回合...")
    test_scenarios = [
        "你看到前方有一个宝箱，右边有一个怪物。",
        "怪物向你冲过来了，你的血量是80%。",
        "怪物被击败，宝箱在你面前。",
    ]

    for i, scene in enumerate(test_scenarios, 1):
        if i > 1:
            time.sleep(2)  # 请求间隔，避免限流
        print(f"\n--- 回合 {i} ---")
        print(f"场景: {scene}")
        action = ai.get_action(game_state_text=scene)
        print(f"动作: {action.action} | 目标: {action.target} | 方向: {action.direction}")
        print(f"信心: {action.confidence} | 推理: {action.reasoning}")

    print("\n--- 经验总结 ---")
    summary = ai.summarize_experience()
    print(summary)

    print("\n--- 经验库 ---")
    print(ai.experience.get_summary())


if __name__ == "__main__":
    main()
