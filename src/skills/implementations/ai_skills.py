# -*- coding: utf-8 -*-
import time
import re
import win32clipboard
import logging
import win32api
import win32con
import cv2
import numpy as np
from src.skills.registry import skill_handler
from src.core.viewport import ViewportManager

logger = logging.getLogger("AISkills")

# [V7.95] 获取共享实例的助手函数
def get_oracle():
    from src.skills.implementations.atomic_skills import get_oracle as _get_oracle
    return _get_oracle()

def get_bridge():
    oracle = get_oracle()
    return getattr(oracle, 'bridge', None)

def _log(msg):
    bridge = get_bridge()
    if bridge:
        bridge._log(f"[AI_SKILL] {msg}")
    else:
        logger.info(msg)

@skill_handler("wait_for_ai_idle")
def wait_for_ai_idle(vm: ViewportManager, timeout=60, **kwargs):
    """[V7.81] 盯盘技能：监测浏览器发送按钮，直到 AI 回复结束"""
    _log(f"正在等待 AI 响应完成 (超时: {timeout}s)...")
    from src.vision.recognition_expert import RecognitionExpert
    from src.vision.capture import VisionCapture
    
    vc = VisionCapture()
    expert = RecognitionExpert(vision_capture=vc)
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        # 1. 抓取全屏图像
        img_path = vc.capture_screen()
        img_np = cv2.imread(img_path)
        
        if img_np is not None:
            # 2. 使用正确的 find_landmark 方法
            res = expert.find_landmark(img_np, ["Send", "发送", "Message", "Chat"])
            if res:
                _log(f"检测到发送按钮恢复 (坐标: {res})，AI 响应已完成。")
                return True
        
        time.sleep(2.5)
    
    _log("等待 AI 响应超时。")
    return False

@skill_handler("extract_ai_clipboard")
def extract_ai_clipboard(vm: ViewportManager, **kwargs):
    """[V7.85] 工业级抓取：定位复制图标并读取剪贴板"""
    _log("正在执行精准决策抓取...")
    
    oracle = get_oracle()
    oracle.action_focus_gpt_window()
    time.sleep(0.8)
    
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
    except: pass
    
    # [V7.97] 强制聚焦：在按 Ctrl+A 之前，先在窗口中心点一下，确保焦点在网页内容区
    cx, cy = win32api.GetSystemMetrics(win32con.SM_CXSCREEN) // 2, win32api.GetSystemMetrics(win32con.SM_CYSCREEN) // 2
    try:
        if hasattr(oracle, 'last_hwnd') and oracle.last_hwnd:
            import win32gui
            w_rect = win32gui.GetWindowRect(oracle.last_hwnd)
            cx = (w_rect[0] + w_rect[2]) // 2
            cy = (w_rect[1] + w_rect[3]) // 2
    except: pass
    
    # 模拟点击中心以激活网页焦点
    win32api.SetCursorPos((cx, cy))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.5)

    res = None
    from src.vision.recognition_expert import RecognitionExpert
    from src.vision.capture import VisionCapture
    vc = VisionCapture()
    expert = RecognitionExpert(vision_capture=vc)
    
    # 抓取当前屏幕寻找复制按钮
    img_path = vc.capture_screen()
    img_np = cv2.imread(img_path)
    if img_np is not None:
        res = expert.find_landmark(img_np, ["Copy", "复制", "Done", "Share"])
        
    if res:
        _log(f"找到交互按钮 at {res}, 正在执行点击...")
        win32api.SetCursorPos((int(res[0]), int(res[1])))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(1.0) 
    else:
        _log("未找到显式按钮，执行强制 Ctrl+A + Ctrl+C...")
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('A'), 0, 0, 0)
        time.sleep(0.2)
        win32api.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(ord('C'), 0, 0, 0)
        time.sleep(0.2)
        win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(1.5)

    try:
        win32clipboard.OpenClipboard()
        text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        
        # [V7.98] 严格清洗：去除两端空白
        if text and text.strip():
            final_text = text.strip()
            _log(f"提取成功，有效数据长度: {len(final_text)}")
            bridge = get_bridge()
            if bridge:
                bridge.context["raw_ai_response"] = final_text
            return True
        else:
            _log("提取结果为空或仅包含空白字符。")
    except Exception as e:
        _log(f"读取剪贴板失败: {e}")
        try: win32clipboard.CloseClipboard()
        except: pass
    
    return False

@skill_handler("parse_scoring_logic")
def parse_scoring_logic(vm: ViewportManager, **kwargs):
    """[V7.90] 语义解析：将 AI 文本映射到 6 维度决策"""
    bridge = get_bridge()
    if not bridge or "raw_ai_response" not in bridge.context:
        _log("解析失败：Context 中无 AI 响应。")
        return False
        
    text = bridge.context["raw_ai_response"]
    # [V7.95] 强制终端打印，确保开发者能看到原始返回
    print("\n" + "="*30 + " AI RESPONSE START " + "="*30)
    print(text)
    print("="*31 + " AI RESPONSE END " + "="*31 + "\n")
    
    clean_preview = text[:50].replace('\n', ' ')
    _log(f"正在执行正则映射... (文本前50字: {clean_preview})")
    
    # 记录到绝对路径文件，防止路径漂移
    try:
        with open(r"D:\Dev\autoplay\records\last_ai_raw.txt", "w", encoding="utf-8") as f:
            f.write(text)
    except: pass

    # 增加对 Markdown 加粗格式的兼容 (如 **Overall**)
    dim_map = {
        "Overall": ["Overall Preference", "Overall", "总体偏好", "综合评价"],
        "Instruction": ["Instruction Following", "Instruction", "指令遵循"],
        "ID": ["ID Preservation", "ID", "人物一致性", "ID一致性"],
        "Content": ["Content Preservation", "Content", "内容一致性", "内容保留"],
        "Visual": ["Visual Quality", "Visual", "视觉质量", "画质"],
        "Generated": ["Less AI Generated", "Generated", "AI感", "AI生成"]
    }
    
    found_count = 0
    for context_key, search_kws in dim_map.items():
        for kw in search_kws:
            # [V19.1] 决策对齐优化：
            # 1. 去掉 re.DOTALL，防止跨行勾搭“理由”里的文字
            # 2. 允许关键词前有序号或 Markdown 符号
            pattern = rf"(?:\d+[\.\s、]+)?(?:\*\*|__)?{kw}(?:\*\*|__)?.*?[:：\s]+.*?(Response A|Response B|Both Good|Both Bad|\bA\b|\bB\b)"
            
            # 使用 finditer 找到所有匹配，并取【最后一个】，确保是最新的一条回复
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                last_match = matches[-1]
                val = last_match.group(1).strip()
                # 归一化 A/B
                if val.upper() == "A": val = "Response A"
                if val.upper() == "B": val = "Response B"
                
                bridge.context[context_key] = val
                _log(f"[DECISION] {context_key} -> {val}")
                found_count += 1
                break
    
    if found_count > 0:
        _log(f"解析成功: {found_count}/6")
        return True
    
    # [V7.93] 故障诊断：如果完全没有解析成功，将原始文本存入文件供开发者查阅
    _log("解析完全失败！已将原始文本存入 records/failed_response.txt")
    with open("records/failed_response.txt", "w", encoding="utf-8") as f:
        f.write(text)
    
    # 尝试最终兜底：在全文中盲搜 Response A/B (针对非结构化回复)
    if "Response A" in text: 
        bridge.context["Overall"] = "Response A"
        _log("触发最终兜底：在全文发现 Response A")
        return True
    if "Response B" in text:
        bridge.context["Overall"] = "Response B"
        _log("触发最终兜底：在全文发现 Response B")
        return True
        
    return False

class AISkillsMixin:
    pass
