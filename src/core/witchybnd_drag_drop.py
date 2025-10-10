#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WitchyBND 模拟拖放处理器 - 使用多线程模拟拖放方式处理DCX文件
基于WitchyBND批量解包程序的设计
"""

import os
import subprocess
import logging
import threading
import time
from typing import Optional, Tuple
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

class WitchyBNDDragDropProcessor:
    """WitchyBND模拟拖放处理器类"""
    
    def __init__(self, witchybnd_path: Optional[str] = None):
        """
        初始化WitchyBND处理器
        
        Args:
            witchybnd_path: WitchyBND.exe的路径，如果为None则自动查找
        """
        if witchybnd_path:
            self.witchybnd_path = witchybnd_path
        else:
            # 自动查找WitchyBND.exe
            self.witchybnd_path = self._find_witchybnd()
        
        # 线程锁，用于线程安全的日志输出
        self.thread_lock = threading.Lock()
        
        logger.info(f"WitchyBND模拟拖放处理器初始化，工具路径: {self.witchybnd_path}")
    
    def _find_witchybnd(self) -> str:
        """自动查找WitchyBND.exe"""
        possible_paths = [
            "tools/WitchyBND/WitchyBND.exe",
            "../WitchyBND/WitchyBND.exe", 
            "../../WitchyBND/WitchyBND.exe",
            "WitchyBND.exe"
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                return abs_path
        
        raise FileNotFoundError("未找到WitchyBND.exe，请确保工具已正确安装")
    
    def _run_witchy_drag_drop(self, target_path: str, timeout: int = 300) -> Tuple[bool, str]:
        """
        使用模拟拖放方式运行WitchyBND
        
        Args:
            target_path: 目标文件路径
            timeout: 超时时间（秒）
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            # 获取目标文件的目录作为工作目录
            target_dir = os.path.dirname(os.path.abspath(target_path))
            
            # 使用shell=True方式执行，这样WitchyBND可以正常访问控制台
            # 这是最接近用户手动拖放的执行方式
            cmd = f'"{self.witchybnd_path}" "{target_path}"'
            
            with self.thread_lock:
                logger.info(f"执行shell命令: {cmd}")
                logger.info(f"工作目录: {target_dir}")
            
            # 使用shell=True执行，让Windows shell处理
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                cwd=target_dir  # 设置正确的工作目录
            )
            
            try:
                # 等待进程完成，自动处理任何提示
                stdout, stderr = process.communicate(input="\n", timeout=timeout)
                return_code = process.returncode
                
                with self.thread_lock:
                    logger.info(f"WitchyBND返回码: {return_code}")
                    if stdout.strip():
                        logger.info(f"WitchyBND输出: {stdout.strip()}")
                    if stderr.strip():
                        # 忽略控制台相关的异常，这些都是预期的
                        console_errors = ["KeyAvailable", "InvalidOperationException", "句柄无效", "Console", "CursorVisible", "TypeInitializationException", "IOException"]
                        if any(error_keyword in stderr for error_keyword in console_errors):
                            logger.debug(f"WitchyBND控制台重定向异常(预期): {stderr.strip()[:200]}...")
                        else:
                            logger.warning(f"WitchyBND错误输出: {stderr.strip()}")
                
                # WitchyBND在控制台重定向环境下可能返回非零码
                # 但这不一定表示解包失败，主要依赖后续的文件检查来判断成功状态
                # 只有在有明确错误输出时才认为是失败
                
                # 检查stdout中是否有明确的错误信息
                if stdout.strip():
                    stdout_clean = stdout.strip()
                    # 检查是否包含真正的错误信息
                    if any(keyword in stdout_clean for keyword in ["解包失败", "错误", "Error", "Exception"]) and \
                       not any(keyword in stdout_clean for keyword in ["DCX解包完成", "Successfully parsed"]):
                        logger.warning(f"WitchyBND输出中发现错误: {stdout_clean}")
                        return False, stdout_clean
                
                logger.info(f"WitchyBND执行完成，返回码: {return_code}，等待文件系统同步...")
                
                # 等待文件系统操作完成
                time.sleep(3)
                return True, ""
                
            except subprocess.TimeoutExpired:
                with self.thread_lock:
                    logger.error("WitchyBND执行超时，终止进程...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False, "执行超时"
                
        except Exception as e:
            error_msg = f"模拟拖放执行异常: {str(e)}"
            with self.thread_lock:
                logger.error(error_msg)
            return False, error_msg
    
    def _check_unpack_output(self, dcx_file_path: str) -> Tuple[bool, str, int]:
        """
        检查DCX解包的输出结果
        
        Args:
            dcx_file_path: DCX文件路径
            
        Returns:
            (是否存在输出, 输出目录路径, 文件数量)
        """
        dcx_dir = os.path.dirname(os.path.abspath(dcx_file_path))
        dcx_basename = os.path.splitext(os.path.basename(dcx_file_path))[0]
        
        # 可能的输出目录名称模式
        possible_patterns = [
            f"{dcx_basename}-wmatbinbnd",
            f"{dcx_basename}-matbinbnd-dcx-wmatbinbnd", 
            f"{dcx_basename}-witchy-bnd4",
            f"{dcx_basename}_unpacked"
        ]
        
        for pattern in possible_patterns:
            output_dir = os.path.join(dcx_dir, pattern)
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                # 统计MATBIN文件数量
                matbin_files = [f for f in os.listdir(output_dir) if f.endswith('.matbin')]
                return True, output_dir, len(matbin_files)
        
        return False, "", 0
    
    def extract_dcx(self, dcx_file: str, use_threading: bool = True) -> str:
        """
        使用模拟拖放方式解包DCX文件
        
        Args:
            dcx_file: DCX文件路径
            use_threading: 是否使用多线程（默认True）
            
        Returns:
            解包后的目录路径
        """
        if not os.path.exists(dcx_file):
            raise FileNotFoundError(f"DCX文件不存在: {dcx_file}")
            
        if not os.path.exists(self.witchybnd_path):
            raise FileNotFoundError(f"WitchyBND工具未找到: {self.witchybnd_path}")
        
        dcx_file = os.path.abspath(dcx_file)
        logger.info(f"开始模拟拖放解包DCX文件: {dcx_file}")
        
        # 检查解包前的状态
        output_exists_before, existing_folder, existing_count = self._check_unpack_output(dcx_file)
        if output_exists_before:
            logger.info(f"发现已存在的解包目录: {existing_folder} ({existing_count} 个MATBIN文件)")
            return existing_folder
        
        if use_threading:
            # 使用线程执行模拟拖放，避免阻塞UI
            result_container = {'success': False, 'error': '', 'output_dir': ''}
            
            def thread_worker():
                success, error = self._run_witchy_drag_drop(dcx_file)
                result_container['success'] = success
                result_container['error'] = error
                
                if success:
                    # 等待一下让文件系统同步
                    time.sleep(1)
                    # 检查解包结果
                    output_exists, output_dir, file_count = self._check_unpack_output(dcx_file)
                    if output_exists:
                        result_container['output_dir'] = output_dir
                        logger.info(f"模拟拖放解包成功: {output_dir} ({file_count} 个MATBIN文件)")
                    else:
                        result_container['success'] = False
                        result_container['error'] = "未找到解包输出目录"
            
            # 启动线程
            thread = threading.Thread(target=thread_worker)
            thread.start()
            thread.join(timeout=360)  # 6分钟超时
            
            if thread.is_alive():
                logger.error("模拟拖放线程超时")
                raise RuntimeError("解包操作超时")
            
            if not result_container['success']:
                raise RuntimeError(f"模拟拖放解包失败: {result_container['error']}")
            
            return result_container['output_dir']
        
        else:
            # 直接执行（非线程）
            success, error = self._run_witchy_drag_drop(dcx_file)
            
            if not success:
                raise RuntimeError(f"模拟拖放解包失败: {error}")
            
            # 检查解包结果
            time.sleep(1)  # 等待文件系统同步
            output_exists, output_dir, file_count = self._check_unpack_output(dcx_file)
            
            if not output_exists:
                raise RuntimeError("模拟拖放解包完成，但未找到输出目录")
            
            logger.info(f"模拟拖放解包成功: {output_dir} ({file_count} 个MATBIN文件)")
            return output_dir
    
    def convert_matbin_to_xml(self, matbin_file: str, use_threading: bool = True) -> str:
        """
        使用模拟拖放方式将MATBIN文件转换为XML
        
        Args:
            matbin_file: MATBIN文件路径
            use_threading: 是否使用多线程（默认True）
            
        Returns:
            生成的XML文件路径
        """
        if not os.path.exists(matbin_file):
            raise FileNotFoundError(f"MATBIN文件不存在: {matbin_file}")
        
        matbin_file = os.path.abspath(matbin_file)
        expected_xml = matbin_file + '.xml'
        
        logger.info(f"开始模拟拖放转换MATBIN到XML: {matbin_file}")
        
        # 检查XML是否已存在
        if os.path.exists(expected_xml):
            logger.info(f"XML文件已存在: {expected_xml}")
            return expected_xml
        
        if use_threading:
            # 使用线程执行模拟拖放
            result_container = {'success': False, 'error': ''}
            
            def thread_worker():
                success, error = self._run_witchy_drag_drop(matbin_file)
                result_container['success'] = success
                result_container['error'] = error
            
            # 启动线程
            thread = threading.Thread(target=thread_worker)
            thread.start()
            thread.join(timeout=120)  # 2分钟超时
            
            if thread.is_alive():
                logger.error("MATBIN转换线程超时")
                raise RuntimeError("MATBIN转换操作超时")
            
            if not result_container['success']:
                raise RuntimeError(f"模拟拖放MATBIN转换失败: {result_container['error']}")
        
        else:
            # 直接执行（非线程）
            success, error = self._run_witchy_drag_drop(matbin_file)
            
            if not success:
                raise RuntimeError(f"模拟拖放MATBIN转换失败: {error}")
        
        # 等待并检查XML文件生成
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            if os.path.exists(expected_xml):
                logger.info(f"模拟拖放MATBIN转换成功: {expected_xml}")
                return expected_xml
        
        raise RuntimeError(f"模拟拖放MATBIN转换完成，但未找到XML文件: {expected_xml}")

# 创建全局实例以保持向后兼容
WitchyBNDProcessor = WitchyBNDDragDropProcessor