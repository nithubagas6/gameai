"""
GameAI Console - Web 服务器
提供可视化界面和 API 代理服务
"""

import json
import time
import sys
import os
import base64
import threading
from pathlib import Path
from flask import Flask, request, Response, jsonify, send_from_directory
from dataclasses import asdict

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_ai_api import GameAI_API, ExperienceManager, GameAction

# ============================
# Flask 应用
# ============================
app = Flask(__name__, static_folder='static')

# 全局经验管理器
experience_manager = ExperienceManager("experiences_web.json")

# 全局截图存储（用于OCR）
current_screenshot = None
screenshot_lock = threading.Lock()

def get_screenshot():
    """获取当前截图"""
    global current_screenshot
    with screenshot_lock:
        return current_screenshot

def set_screenshot(image_bytes):
    """设置当前截图"""
    global current_screenshot
    with screenshot_lock:
        current_screenshot = image_bytes

# ============================
# 静态文件服务
# ============================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# ============================
# 截图上传接口
# ============================
@app.route('/api/upload-screenshot', methods=['POST'])
def upload_screenshot():
    """上传游戏截图用于OCR识别"""
    try:
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            image_bytes = file.read()
        elif request.json and 'image' in request.json:
            # base64编码的图片
            image_data = request.json['image']
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            return jsonify({'success': False, 'message': '未收到截图数据'})
        
        set_screenshot(image_bytes)
        return jsonify({'success': True, 'message': '截图已上传'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@app.route('/api/get-ocr', methods=['POST'])
def get_ocr():
    """对当前截图进行OCR识别"""
    screenshot = get_screenshot()
    if not screenshot:
        return jsonify({'success': False, 'message': '没有可用的截图'})
    
    try:
        from game_ai_api import LocalOCR
        ocr = LocalOCR()
        text = ocr.recognize(image_bytes=screenshot)
        return jsonify({'success': True, 'text': text})
    except Exception as e:
        return jsonify({'success': False, 'message': f'OCR失败: {str(e)}'})

# ============================
# API 接口
# ============================

@app.route('/api/fetch-models', methods=['POST'])
def fetch_models():
    """获取可用模型列表"""
    data = request.get_json()
    base_url = data.get('base_url', '').rstrip('/')
    api_key = data.get('api_key', '')
    
    if not base_url:
        return jsonify({
            'success': False,
            'message': '请填写 API URL',
            'models': []
        })
    
    if not api_key:
        return jsonify({
            'success': False,
            'message': '请填写 API Key',
            'models': []
        })
    
    try:
        import requests as req
        # 尝试获取模型列表
        resp = req.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15
        )
        
        if resp.status_code == 200:
            models_data = resp.json()
            models = sorted([m['id'] for m in models_data.get('data', [])])
            
            if models:
                return jsonify({
                    'success': True,
                    'message': f'获取到 {len(models)} 个模型',
                    'models': models
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '该接口未返回模型列表',
                    'models': []
                })
        else:
            return jsonify({
                'success': False,
                'message': f'请求失败: HTTP {resp.status_code}',
                'models': []
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接失败: {str(e)}',
            'models': []
        })

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """测试 API 连接（已废弃，使用 fetch-models 替代）"""
    return fetch_models()

@app.route('/api/scenario', methods=['POST'])
def send_scenario():
    """发送游戏场景，流式返回 AI 决策"""
    data = request.get_json()
    base_url = data.get('base_url', '')
    api_key = data.get('api_key', '')
    model = data.get('model', 'gpt-5.4-mini')
    scenario = data.get('scenario', '')
    
    if not scenario:
        return jsonify({
            'success': False,
            'message': '请输入游戏场景描述'
        })
    
    def generate():
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': 'AI 正在思考...'})}\n\n"
            
            # 创建 GameAI_API 实例
            ai = GameAI_API(
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            
            # 获取决策
            action = ai.get_action(game_state_text=scenario)
            
            # 构建响应数据
            decision_data = {
                'action': action.action,
                'target': action.target,
                'direction': action.direction,
                'position': action.position,
                'confidence': action.confidence,
                'reasoning': action.reasoning
            }
            
            # 添加到经验管理器
            experience_manager.add(
                observation=scenario[:500],
                action=json.dumps(decision_data, ensure_ascii=False),
                result=action.reasoning,
                lesson=''
            )
            
            # 发送完成事件
            yield f"data: {json.dumps({'type': 'complete', 'data': decision_data})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'请求失败: {str(e)}'})}\n\n"
        
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/run-goal', methods=['POST'])
def run_goal():
    """执行目标驱动的任务，流式返回执行过程"""
    data = request.get_json()
    base_url = data.get('base_url', '')
    api_key = data.get('api_key', '')
    model = data.get('model', 'gpt-5.4-mini')
    goal = data.get('goal', '')
    max_steps = data.get('max_steps', 10)
    initial_game_state = data.get('game_state', '')
    
    if not goal:
        return jsonify({
            'success': False,
            'message': '请输入目标描述'
        })
    
    def generate():
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': f'开始执行目标: {goal}'})}\n\n"
            
            # 创建 GameAI_API 实例
            ai = GameAI_API(
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            
            step_history = []
            current_game_state = initial_game_state
            goal_achieved = False
            
            for step in range(1, max_steps + 1):
                # 发送步骤开始事件
                yield f"data: {json.dumps({'type': 'step_start', 'step': step, 'max_steps': max_steps})}\n\n"
                
                # 发送OCR识别事件
                yield f"data: {json.dumps({'type': 'ocr_start', 'step': step})}\n\n"
                
                # 获取AI决策（会自动进行OCR识别）
                action = ai.get_action_for_goal(
                    goal=goal,
                    game_state_text=current_game_state,
                    step_history=step_history,
                    screenshot_func=get_screenshot
                )
                
                # 获取动作列表
                actions = getattr(action, 'actions', [])
                
                # 构建动作数据（包含多个动作）
                action_data = {
                    'actions': actions,
                    'confidence': action.confidence,
                    'reasoning': action.reasoning,
                    'progress': getattr(action, 'progress', '')
                }
                
                # 发送动作事件
                yield f"data: {json.dumps({'type': 'step_action', 'step': step, 'action': action_data})}\n\n"
                
                # 检查目标是否达成
                goal_achieved = getattr(action, 'goal_achieved', False)
                
                # 构建结果数据
                result_data = {
                    'step': step,
                    'actions': actions,
                    'reasoning': action.reasoning,
                    'progress': getattr(action, 'progress', '')
                }
                
                # 发送步骤完成事件
                yield f"data: {json.dumps({'type': 'step_complete', 'step': step, 'result': result_data})}\n\n"
                
                # 添加到步骤历史
                actions_summary = ', '.join([a.get('type', 'unknown') for a in actions])
                step_history.append(f"动作序列: [{actions_summary}], 进度: {getattr(action, 'progress', '')}")
                
                # 添加到经验管理器
                experience_manager.add(
                    observation=f"目标: {goal}, 步骤 {step}",
                    action=json.dumps(action_data, ensure_ascii=False),
                    result=action.reasoning,
                    lesson=''
                )
                
                # 如果目标达成，发送成功事件并结束
                if goal_achieved:
                    yield f"data: {json.dumps({'type': 'goal_achieved', 'step': step, 'message': getattr(action, 'progress', '目标已完成')})}\n\n"
                    break
                
                # 更新游戏状态（在实际应用中，这里应该从游戏获取最新状态）
                # 由于我们没有实际的游戏环境，这里使用模拟的状态更新
                current_game_state = f"步骤 {step} 已执行动作序列: {actions_summary}. {getattr(action, 'progress', '')}"
            
            # 如果达到最大步数仍未完成
            if not goal_achieved and step >= max_steps:
                yield f"data: {json.dumps({'type': 'max_steps_reached', 'step': step})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'执行失败: {str(e)}'})}\n\n"
        
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/api/experiences', methods=['GET'])
def get_experiences():
    """获取经验库"""
    experiences = [asdict(e) for e in experience_manager.experiences]
    return jsonify({
        'success': True,
        'experiences': experiences
    })

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """总结经验"""
    data = request.get_json()
    base_url = data.get('base_url', '')
    api_key = data.get('api_key', '')
    model = data.get('model', 'gpt-5.4-mini')
    
    try:
        # 创建 GameAI_API 实例
        ai = GameAI_API(
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        
        # 加载历史经验
        ai.experience = experience_manager
        
        # 总结经验
        summary = ai.summarize_experience()
        
        return jsonify({
            'success': True,
            'message': '经验总结完成',
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'总结失败: {str(e)}'
        })

@app.route('/api/export', methods=['GET'])
def export_experiences():
    """导出经验库"""
    experiences = [asdict(e) for e in experience_manager.experiences]
    return Response(
        json.dumps(experiences, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={
            'Content-Disposition': 'attachment; filename=experiences.json'
        }
    )

# ============================
# 主程序入口
# ============================
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="GameAI Console - Web 服务器")
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8080, help='监听端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()
    
    print("=" * 50)
    print("  GameAI Console - Web 服务器")
    print("=" * 50)
    print(f"  访问地址: http://localhost:{args.port}")
    print("=" * 50)
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )
