#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WitchyBND工具集成模块 - 使用模拟拖放方式
用于处理.dcx文件的解包和.matbin文件的转换
基于WitchyBND批量解包程序的模拟拖放设计
"""

import os
import subprocess
import tempfile
import shutil
import logging
import threading
import time
from typing import List, Dict, Optional, Tuple, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils.resource_path import get_tools_path, get_data_path

logger = logging.getLogger(__name__)

class WitchyBNDProcessor:
    """WitchyBND工具处理器 - 模拟拖放版本"""
    
    def __init__(self, witchybnd_path: str = None, max_threads: int = 32):
        """
        初始化WitchyBND处理器
        
        Args:
            witchybnd_path: WitchyBND工具路径，如果为None则自动查找
            max_threads: 最大并发线程数，默认32
        """
        self.witchybnd_path = witchybnd_path or self._find_witchybnd_path()
        self.temp_dir = None
        self.thread_lock = threading.Lock()  # 线程安全锁
        self.max_threads = max_threads  # 最大并发线程数
        
        logger.info(f"WitchyBND处理器初始化 - 工具路径: {self.witchybnd_path}, 最大线程数: {self.max_threads}")
        
    def _find_witchybnd_path(self) -> str:
        """自动查找WitchyBND工具路径（支持打包环境）"""
        # 优先使用资源路径辅助模块获取打包环境下的路径
        packed_path = get_tools_path("WitchyBND/WitchyBND.exe")
        if os.path.exists(packed_path):
            return packed_path
        
        # 兼容开发环境的相对路径
        possible_paths = [
            "tools/WitchyBND/WitchyBND.exe",  # 项目内置工具 (首选)
            "WitchyBND/WitchyBND.exe",        # 相对路径
            "../WitchyBND/WitchyBND.exe",     # 上级目录
            "../../WitchyBND/WitchyBND.exe",  # 上上级目录
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # 如果找不到，返回默认路径
        return get_tools_path("WitchyBND/WitchyBND.exe")
    
    def _run_witchy_drag_drop(self, target_path: str, timeout: int = 300) -> Tuple[bool, str]:
        """
        使用改进的方式执行WitchyBND模拟拖放操作
        参考批量解包工具的成功实现
        
        Args:
            target_path: 目标文件路径
            timeout: 超时时间（秒）- 默认5分钟，大文件需要更长时间
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            with self.thread_lock:
                logger.info(f"使用批量解包工具的成功实现方式")
                logger.info(f"WitchyBND路径: {self.witchybnd_path}")
                logger.info(f"目标文件: {target_path}")
            
            # 构建命令 - 直接将目标路径作为参数传递给exe
            cmd = [self.witchybnd_path, target_path]
            
            with self.thread_lock:
                logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 使用批量解包工具的成功方法：
            # 1. 使用Popen而不是run
            # 2. 重定向stdin但不重定向stdout/stderr
            # 3. 让WitchyBND在stdin重定向时自动跳过"Press any key"等待
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,  # 重定向stdin以避免"Press any key"等待
                text=True,
                encoding='utf-8',
                errors='ignore'
                # 不重定向stdout/stderr，让WitchyBND控制台正常显示
            )
            
            # 等待进程完成，设置合理的超时时间
            try:
                return_code = process.wait(timeout=timeout)
                
                with self.thread_lock:
                    logger.info(f"WitchyBND返回码: {return_code}")
                
                # 重要：WitchyBND在stdin重定向时会返回非零码但实际解包成功
                # 控制台交互异常（InvalidOperationException）不影响实际处理结果
                # 我们主要依赖后续的文件检查来判断成功，而不是返回码
                if return_code == 3762504530:
                    logger.info("WitchyBND控制台错误（可忽略），通过文件检查确认成功")
                    return True, ""
                elif return_code == 0:
                    logger.info("WitchyBND执行成功")
                    return True, ""
                else:
                    # 其他非零返回码，包括控制台交互异常，仍然返回成功，依赖文件检查
                    with self.thread_lock:
                        logger.info(f"WitchyBND返回非零码: {return_code}（通常因控制台交互异常，实际处理可能成功）")
                    return True, ""
                    
            except subprocess.TimeoutExpired:
                with self.thread_lock:
                    logger.error(f"WitchyBND执行超时（{timeout}秒）")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    with self.thread_lock:
                        logger.error("强制终止WitchyBND进程")
                return False, f"WitchyBND执行超时（{timeout}秒）"
                
        except FileNotFoundError:
            error_msg = f"WitchyBND工具未找到: {self.witchybnd_path}"
            with self.thread_lock:
                logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"WitchyBND执行异常: {str(e)}"
            with self.thread_lock:
                logger.error(error_msg)
            return False, error_msg

    def _run_witchy_batch(self, target_paths: List[str], timeout: int = 300) -> Tuple[bool, str]:
        """
        批量执行 WitchyBND 操作
        
        Args:
            target_paths: 目标文件路径列表
            timeout: 超时时间
            
        Returns:
            (成功标志, 错误信息)
        """
        if not target_paths:
            return True, ""
            
        try:
            # 构建命令 - 将所有目标路径作为参数传递
            cmd = [self.witchybnd_path] + target_paths
            
            # 检查命令行长度限制 (Windows 限制约 32767 字符)
            cmd_len = sum(len(arg) + 1 for arg in cmd)
            if cmd_len > 32000:
                logger.warning(f"命令行过长 ({cmd_len}), 建议分更小的批次")
            
            # 使用Popen而不是run
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            try:
                return_code = process.wait(timeout=timeout)
                
                if return_code == 0 or return_code == 3762504530:
                    return True, ""
                else:
                    return True, f"返回码 {return_code}" # 同样依赖文件检查
                    
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False, f"批量操作超时（{timeout}秒）"
                
        except Exception as e:
            logger.error(f"WitchyBND批量执行异常: {str(e)}")
            return False, str(e)


    def _check_unpack_output(self, dcx_file_path: str) -> Tuple[bool, str, int]:
        """
        检查DCX解包的输出结果 - 改进版本，支持更广泛的文件夹命名模式
        
        Args:
            dcx_file_path: DCX文件路径
            
        Returns:
            (是否存在输出, 输出目录路径, 文件数量)
        """
        dcx_dir = os.path.dirname(os.path.abspath(dcx_file_path))
        dcx_basename = os.path.splitext(os.path.basename(dcx_file_path))[0]
        # 处理点号格式，转换为短横线格式（WitchyBND实际输出格式）
        dcx_basename_dash = dcx_basename.replace('.', '-')
        
        logger.info(f"检查解包输出 - 目录: {dcx_dir}, 基础名: {dcx_basename}, 短横线格式: {dcx_basename_dash}")
        
        # 可能的输出目录名称模式 - 修复版本，确保正确的模式优先
        # 对于 allmaterial.matbinbnd.dcx，实际输出是 allmaterial-matbinbnd-dcx-wmatbinbnd
        # 对于老版本 allmaterialbnd.mtdbnd.dcx，实际输出是 allmaterialbnd-mtdbnd-dcx-wmtdbnd
        base_name_no_extension = dcx_basename.split('.')[0]  # allmaterial 或 allmaterialbnd
        
        possible_patterns = [
            # 最常见的模式：filename-matbinbnd-dcx-wmatbinbnd (新版本)
            f"{base_name_no_extension}-matbinbnd-dcx-wmatbinbnd",  # allmaterial-matbinbnd-dcx-wmatbinbnd
            # 老版本的模式：filename-mtdbnd-dcx-wmtdbnd
            f"{base_name_no_extension}-mtdbnd-dcx-wmtdbnd",  # allmaterialbnd-mtdbnd-dcx-wmtdbnd
            # 其他可能的模式
            f"{dcx_basename_dash}-wmatbinbnd",
            f"{dcx_basename_dash}-wmtdbnd",  # 老版本变体
            f"{dcx_basename_dash}-matbinbnd-dcx-wmatbinbnd", 
            f"{dcx_basename_dash}-mtdbnd-dcx-wmtdbnd",  # 老版本变体
            f"{dcx_basename_dash}-witchy-bnd4",
            f"{dcx_basename_dash}_unpacked",
            f"{dcx_basename}-wmatbinbnd",  # 保留原格式作为备用
            f"{dcx_basename}-matbinbnd-dcx-wmatbinbnd",
            f"{dcx_basename}-witchy-bnd4",
            f"{dcx_basename}_unpacked",
            # 简单模式
            f"{dcx_basename_dash}",
            f"{dcx_basename}",
            f"unpacked_{dcx_basename_dash}",
            f"unpacked_{dcx_basename}",
            f"{dcx_basename_dash}_extracted",
            f"{dcx_basename}_extracted"
        ]
        
        logger.info(f"尝试精确匹配模式: {possible_patterns[:4]}...")  # 只显示前几个避免日志过长
        
        # 先精确匹配
        for pattern in possible_patterns:
            output_dir = os.path.join(dcx_dir, pattern)
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                # 统计MATBIN文件数量（包括子目录）
                try:
                    matbin_count = self._count_matbin_files_recursive(output_dir)
                    if matbin_count > 0:  # 确保有matbin文件
                        logger.info(f"精确匹配成功: {output_dir}, MATBIN文件数: {matbin_count}")
                        return True, output_dir, matbin_count
                except OSError:
                    continue
        
        # 如果精确匹配失败，尝试更强化的智能搜索
        logger.info("精确匹配失败，启动增强智能搜索...")
        
        # 获取解包前的目录状态
        if not hasattr(self, '_original_dir_items'):
            try:
                original_items = set(os.listdir(dcx_dir))
            except OSError:
                original_items = set()
        else:
            original_items = self._original_dir_items
        
        # 查找新出现的目录
        try:
            current_items = set(os.listdir(dcx_dir))
            new_dirs = current_items - original_items
            
            logger.info(f"发现新目录: {list(new_dirs)}")
            
            # 增强的搜索策略
            # 1. 基础搜索名称
            search_terms = [dcx_basename, dcx_basename_dash]
            if '.' in dcx_basename:
                search_terms.append(dcx_basename.split('.')[0])  # 第一部分，如 allmaterial
            
            # 2. 优先检查新出现的目录，因为WitchyBND会创建新目录
            best_candidates = []
            
            for item in new_dirs:
                item_path = os.path.join(dcx_dir, item)
                if os.path.isdir(item_path):
                    try:
                        # 使用递归搜索统计MATBIN文件
                        matbin_count = self._count_matbin_files_recursive(item_path)
                        if matbin_count > 0:
                            # 计算匹配度分数
                            score = 0
                            item_lower = item.lower()
                            
                            # 检查关键词匹配
                            for search_term in search_terms:
                                if search_term.lower() in item_lower:
                                    score += 10  # 关键词匹配得高分
                            
                            # 检查WitchyBND典型后缀
                            if any(suffix in item_lower for suffix in ['wmatbinbnd', 'matbinbnd', 'witchy', 'bnd']):
                                score += 5
                            
                            # 检查是否包含解包相关词汇
                            if any(word in item_lower for word in ['unpacked', 'extracted', 'dcx']):
                                score += 3
                            
                            best_candidates.append((item_path, matbin_count, score))
                            logger.info(f"发现候选目录: {item_path}, MATBIN数: {matbin_count}, 匹配分数: {score}")
                    except OSError:
                        continue
            
            # 选择最佳候选目录（优先匹配分数，然后是文件数量）
            if best_candidates:
                best_candidate = max(best_candidates, key=lambda x: (x[2], x[1]))  # (分数, 文件数)
                logger.info(f"智能搜索成功（最佳候选）: {best_candidate[0]}, MATBIN文件数: {best_candidate[1]}, 分数: {best_candidate[2]}")
                return True, best_candidate[0], best_candidate[1]
                        
            # 3. 最后尝试：任何包含matbin/mtd文件的新目录（即使没有关键词匹配）
            matbin_dirs = []
            for item in new_dirs:
                item_path = os.path.join(dcx_dir, item)
                if os.path.isdir(item_path):
                    try:
                        # 支持新版本的.matbin和老版本的.mtd文件
                        matbin_files = [f for f in os.listdir(item_path) 
                                       if f.endswith('.matbin') or f.endswith('.mtd')]
                        if len(matbin_files) > 0:
                            matbin_dirs.append((item_path, len(matbin_files)))
                    except OSError:
                        continue
            
            # 如果找到了包含MATBIN文件的目录，选择文件最多的那个
            if matbin_dirs:
                best_dir = max(matbin_dirs, key=lambda x: x[1])
                logger.info(f"通用智能搜索成功（最佳候选）: {best_dir[0]}, MATBIN文件数: {best_dir[1]}")
                return True, best_dir[0], best_dir[1]
                
            # 4. 终极策略：检查所有现有目录中的MATBIN文件
            logger.info("新目录搜索失败，检查所有现有目录...")
            for item in current_items:
                item_path = os.path.join(dcx_dir, item)
                if os.path.isdir(item_path):
                    try:
                        matbin_count = self._count_matbin_files_recursive(item_path)
                        if matbin_count > 0:
                            # 检查是否包含DCX相关关键词
                            for search_term in search_terms:
                                if search_term.lower() in item.lower():
                                    logger.info(f"终极搜索成功: {item_path}, MATBIN文件数: {matbin_count}")
                                    return True, item_path, matbin_count
                    except OSError:
                        continue
                        
        except OSError as e:
            logger.error(f"目录访问错误: {e}")
        
        logger.info("所有搜索策略都失败")
        return False, "", 0
    
    def _count_matbin_files_recursive(self, directory: str) -> int:
        """
        递归统计目录中的MATBIN/MTD文件数量
        支持新版本的.matbin和老版本的.mtd文件
        
        Args:
            directory: 要搜索的目录
            
        Returns:
            MATBIN/MTD文件总数
        """
        count = 0
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.matbin') or file.endswith('.mtd'):
                        count += 1
        except OSError:
            pass
        return count

    def extract_dcx(self, dcx_file: str, output_dir: str = None) -> str:
        """
        使用模拟拖放方式解包DCX文件
        
        Args:
            dcx_file: DCX文件路径
            output_dir: 输出目录（暂时忽略，使用默认输出位置）
            
        Returns:
            解包后的目录路径
        """
        if not os.path.exists(dcx_file):
            raise FileNotFoundError(f"DCX文件不存在: {dcx_file}")
            
        if not os.path.exists(self.witchybnd_path):
            raise FileNotFoundError(f"WitchyBND工具未找到: {self.witchybnd_path}")
        
        # 跳过文件验证，因为文件本身没有损坏，问题在于解析逻辑
        
        dcx_file = os.path.abspath(dcx_file)
        dcx_dir = os.path.dirname(dcx_file)
        logger.info(f"开始模拟拖放解包DCX文件: {dcx_file}")
        logger.info(f"解包将在原目录自动生成: {dcx_dir}")
        
        # 记录解包前的目录状态
        try:
            self._original_dir_items = set(os.listdir(dcx_dir))
            logger.info(f"记录解包前目录项目: {len(self._original_dir_items)} 个")
        except OSError:
            self._original_dir_items = set()
            logger.warning("无法记录解包前目录状态")
        
        # 不要在解包前检查解包目录是否存在，因为WitchyBND会自动生成
        # 直接开始解包过程
        
        # 使用多线程执行模拟拖放，避免阻塞UI
        result_container = {'success': False, 'error': '', 'output_dir': ''}
        
        def thread_worker():
            success, error = self._run_witchy_drag_drop(dcx_file, timeout=300)  # 5分钟超时
            result_container['success'] = success
            result_container['error'] = error
            
            if success:
                # 等待文件系统同步，给WitchyBND足够时间完成解包
                logger.info("WitchyBND解包完成，等待文件系统同步...")
                time.sleep(5)  # 增加等待时间到5秒
                
                # 检查解包结果
                output_exists, output_dir, file_count = self._check_unpack_output(dcx_file)
                if output_exists:
                    result_container['output_dir'] = output_dir
                    logger.info(f"自动解包成功: {output_dir} ({file_count} 个MATBIN文件)")
                else:
                    # 再次尝试检查，有些情况下需要更多时间
                    logger.info("首次检查未找到，等待更多时间...")
                    time.sleep(3)
                    output_exists, output_dir, file_count = self._check_unpack_output(dcx_file)
                    if output_exists:
                        result_container['output_dir'] = output_dir
                        logger.info(f"自动解包成功(延迟检测): {output_dir} ({file_count} 个MATBIN文件)")
                    else:
                        result_container['success'] = False
                        result_container['error'] = "模块配置数据丢失，未找到解包数据"
                        # 详细调试信息
                        try:
                            current_items = set(os.listdir(dcx_dir))
                            new_items = current_items - self._original_dir_items
                            logger.error(f"调试信息 - 新出现的项目: {list(new_items)}")
                            
                            # 列出所有可能相关的目录
                            dcx_basename = os.path.splitext(os.path.basename(dcx_file))[0]
                            related_items = [item for item in current_items 
                                           if dcx_basename.split('.')[0].lower() in item.lower()]
                            logger.error(f"调试信息 - 相关项目: {related_items}")
                        except Exception as debug_e:
                            logger.error(f"调试信息收集失败: {debug_e}")
            else:
                # 如果WitchyBND本身报告了错误，直接使用该错误信息
                logger.error(f"WitchyBND执行失败: {error}")
                # 根据错误类型提供更友好的错误消息和解决建议
                if error and any(keyword in error for keyword in ["DCX解包完成", "读取配置数据", "未找到解包数据"]):
                    # 这可能是WitchyBND的中文错误输出
                    result_container['error'] = error
                elif "DCX文件格式无效" in error or "已损坏" in error:
                    result_container['error'] = f"{error}\n\n解决建议：\n1. 确认文件确实是DCX格式\n2. 重新下载或获取文件\n3. 检查文件是否完整（未被截断）"
                elif "错误码: 3762504530" in error:
                    result_container['error'] = "DCX文件无法被WitchyBND处理\n\n可能原因：\n1. 文件不是有效的DCX格式\n2. 文件已损坏或不完整\n3. WitchyBND版本不支持此DCX文件\n\n建议：\n- 检查文件来源和完整性\n- 尝试使用其他DCX工具验证文件"
                elif error:
                    result_container['error'] = f"WitchyBND处理失败: {error}"
                else:
                    result_container['error'] = "WitchyBND执行失败，原因未知"
        
        # 启动线程
        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join(timeout=300)  # 增加超时到5分钟，适应大文件处理
        
        if thread.is_alive():
            logger.error("解包操作超时")
            raise TimeoutError("DCX解包操作超时")
        
        if not result_container['success']:
            error_msg = result_container['error'] or "解包失败"
            logger.error(f"DCX解包失败: {error_msg}")
            
            # 创建详细的错误报告
            error_report = {
                'dcx_file': dcx_file,
                'error_message': error_msg,
                'dcx_dir': dcx_dir,
                'witchybnd_path': self.witchybnd_path,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 尝试收集更多调试信息
            try:
                current_items = list(os.listdir(dcx_dir))
                error_report['directory_contents'] = current_items
                
                if hasattr(self, '_original_dir_items'):
                    new_items = set(current_items) - self._original_dir_items
                    error_report['new_items'] = list(new_items)
                    
                # 检查WitchyBND工具是否存在且可执行
                error_report['witchybnd_exists'] = os.path.exists(self.witchybnd_path)
                
                # 记录到文件用于调试
                debug_log_path = os.path.join(dcx_dir, f"dcx_error_debug_{int(time.time())}.log")
                with open(debug_log_path, 'w', encoding='utf-8') as debug_file:
                    import json
                    json.dump(error_report, debug_file, ensure_ascii=False, indent=2)
                    
                logger.info(f"错误调试信息已保存到: {debug_log_path}")
                
            except Exception as debug_e:
                logger.error(f"收集调试信息时发生错误: {debug_e}")
            
            raise RuntimeError(f"DCX解包失败: {error_msg}")
        
        if not result_container['output_dir']:
            raise RuntimeError("解包完成但未找到输出目录")
        
        return result_container['output_dir']
    
    def extract_matbin_to_xml(self, matbin_file: str, output_dir: str = None) -> str:
        """
        使用模拟拖放方式将MATBIN/MTD文件转换为XML
        支持新版本的.matbin和老版本的.mtd文件
        
        Args:
            matbin_file: MATBIN/MTD文件路径
            output_dir: 输出目录（暂时忽略，使用默认输出位置）
            
        Returns:
            生成的XML文件路径
        """
        if not os.path.exists(matbin_file):
            raise FileNotFoundError(f"材质文件不存在: {matbin_file}")
        
        matbin_file = os.path.abspath(matbin_file)
        expected_xml = matbin_file + '.xml'
        
        # 判断文件类型用于日志
        file_type = "MTD" if matbin_file.endswith('.mtd') else "MATBIN"
        logger.info(f"开始模拟拖放转换{file_type}到XML: {matbin_file}")
        
        # 检查XML是否已存在
        if os.path.exists(expected_xml):
            logger.info(f"XML文件已存在: {expected_xml}")
            return expected_xml
        
        # 使用多线程执行模拟拖放
        result_container = {'success': False, 'error': ''}
        
        def thread_worker():
            success, error = self._run_witchy_drag_drop(matbin_file, timeout=300)  # 5分钟超时
            result_container['success'] = success
            result_container['error'] = error
        
        # 启动线程
        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join(timeout=300)  # 增加超时到5分钟，适应大文件处理
        
        if thread.is_alive():
            logger.error("MATBIN转换线程超时")
            raise RuntimeError("MATBIN转换操作超时")
        
        if not result_container['success']:
            raise RuntimeError(f"模拟拖放{file_type}转换失败: {result_container['error']}")
        
        # 等待并检查XML文件生成
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            if os.path.exists(expected_xml):
                logger.info(f"模拟拖放{file_type}转换成功: {expected_xml}")
                return expected_xml
        
        raise RuntimeError(f"模拟拖放{file_type}转换完成，但未找到XML文件: {expected_xml}")
    
    def pack_xml_to_matbin(self, xml_file: str, output_dir: str = None) -> str:
        """
        使用模拟拖放方式将XML文件封包为MATBIN或MTD
        
        Args:
            xml_file: XML文件路径
            output_dir: 输出目录（暂时忽略，使用默认输出位置）
            
        Returns:
            生成的.matbin或.mtd文件路径
        """
        if not os.path.exists(xml_file):
            raise FileNotFoundError(f"XML文件不存在: {xml_file}")
        
        # 检查文件命名格式 - 支持 .matbin.xml 和 .mtd.xml
        xml_filename = os.path.basename(xml_file)
        is_matbin = xml_filename.endswith('.matbin.xml')
        is_mtd = xml_filename.endswith('.mtd.xml')
        
        if not is_matbin and not is_mtd:
            raise ValueError(
                f"XML文件命名格式错误: {xml_filename}\n\n"
                f"正确的命名格式应该是:\n"
                f"  - 艾尔登法环(新版本): *.matbin.xml\n"
                f"  - 只狼(老版本): *.mtd.xml\n\n"
                f"例如:\n"
                f"  - C[c0010]_Arts_horn.matbin.xml (艾尔登法环)\n"
                f"  - C[AMSN]_Cloth_Decal.mtd.xml (只狼)\n\n"
                f"请将文件重命名为正确格式后再试。"
            )
        
        xml_file = os.path.abspath(xml_file)
        # 根据格式确定输出文件类型
        base_name = os.path.splitext(xml_file)[0]  # 移除 .xml
        
        if is_matbin:
            # .matbin.xml -> .matbin
            expected_output = base_name  # base_name 已经是 xxx.matbin
            file_type = "MATBIN"
            output_ext = ".matbin"
        else:
            # .mtd.xml -> .mtd
            expected_output = base_name  # base_name 已经是 xxx.mtd
            file_type = "MTD"
            output_ext = ".mtd"
        
        logger.info(f"开始模拟拖放转换XML到{file_type}: {xml_file}")
        
        # 检查输出文件是否已存在
        if os.path.exists(expected_output):
            logger.info(f"{file_type}文件已存在: {expected_output}")
            return expected_output
        
        # 使用多线程执行模拟拖放
        result_container = {'success': False, 'error': ''}
        
        def thread_worker():
            success, error = self._run_witchy_drag_drop(xml_file, timeout=300)  # 5分钟超时
            result_container['success'] = success
            result_container['error'] = error
        
        # 启动线程
        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join(timeout=300)  # 增加超时到5分钟，适应大文件处理
        
        if thread.is_alive():
            logger.error(f"XML封包线程超时")
            raise RuntimeError(f"XML封包操作超时")
        
        if not result_container['success']:
            error_msg = result_container['error']
            # 提供更详细的错误信息和解决建议
            detailed_error = (
                f"模拟拖放XML封包失败: {error_msg}\n\n"
                f"请检查以下几点:\n"
                f"1. XML文件命名格式是否正确 (*{output_ext}.xml)\n"
                f"   当前文件: {xml_filename}\n"
                f"2. XML文件内容是否符合{file_type}格式\n"
                f"3. WitchyBND工具是否正常工作\n"
                f"4. 文件路径中是否包含特殊字符"
            )
            raise RuntimeError(detailed_error)
        
        # 等待并检查输出文件生成
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            if os.path.exists(expected_output):
                logger.info(f"模拟拖放XML封包成功: {expected_output}")
                return expected_output
        
        # 如果预期位置没有找到，尝试在同目录下查找相关的输出文件
        xml_dir = os.path.dirname(xml_file)
        xml_basename = os.path.splitext(os.path.basename(xml_file))[0]
        
        for file in os.listdir(xml_dir):
            if file.endswith(output_ext) and xml_basename in file:
                output_file = os.path.join(xml_dir, file)
                logger.info(f"找到生成的{file_type}文件: {output_file}")
                return output_file
        
        # 提供详细的失败信息
        raise RuntimeError(
            f"模拟拖放XML封包完成，但未找到{file_type}文件\n\n"
            f"预期文件位置: {expected_output}\n"
            f"请检查:\n"
            f"1. XML文件命名格式: {xml_filename}\n"
            f"2. 是否应该命名为: *{output_ext}.xml 格式\n"
            f"3. WitchyBND是否成功处理了文件"
        )
    
    def batch_extract_matbins(self, directory: str, preserve_structure: bool = True,
                               progress_callback: Callable[[int, int, str], None] = None) -> List[str]:
        """
        批量多线程解包目录中的所有.matbin/.mtd文件
        支持新版本的.matbin和老版本的.mtd文件
        
        Args:
            directory: 包含.matbin/.mtd文件的目录
            preserve_structure: 是否保持目录结构
            progress_callback: 进度回调函数 (current, total, filename)
            
        Returns:
            生成的XML文件列表
        """
        # 收集所有MATBIN/MTD文件
        matbin_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                # 支持新版本的.matbin和老版本的.mtd文件
                if file.endswith('.matbin') or file.endswith('.mtd'):
                    matbin_path = os.path.join(root, file)
                    matbin_files.append(matbin_path)
        
        if not matbin_files:
            logger.warning(f"在目录 {directory} 中未找到MATBIN/MTD文件")
            return []
        
        logger.info(f"发现 {len(matbin_files)} 个材质文件(.matbin/.mtd)，开始多线程批量转换...")
        
        # 使用多线程批处理方法，传递进度回调
        def internal_callback(current, total, filename, status):
            if progress_callback:
                progress_callback(current, total, filename)
            if current % 10 == 0 or current == total:  # 每10个文件或完成时报告进度
                logger.info(f"转换进度: {current}/{total} - {filename} - {status}")
        
        # 调用多线程批处理方法
        results = self.extract_matbin_to_xml_batch(matbin_files, callback=internal_callback)
        
        # 收集成功转换的XML文件
        xml_files = [xml_file for xml_file in results.values() if xml_file]
        
        logger.info(f"批量解包完成，共处理 {len(xml_files)}/{len(matbin_files)} 个文件")
        return xml_files
    
    def cleanup_xml_files(self, xml_files: List[str]):
        """
        清理XML文件，保留.matbin源文件
        只删除成功解析的XML文件
        
        Args:
            xml_files: 要清理的XML文件列表
        """
        if not xml_files:
            logger.info("没有XML文件需要清理")
            return
            
        cleaned_count = 0
        failed_count = 0
        
        for xml_file in xml_files:
            try:
                if os.path.exists(xml_file):
                    os.remove(xml_file)
                    cleaned_count += 1
                    logger.debug(f"已删除成功解析的XML文件: {os.path.basename(xml_file)}")
                else:
                    logger.warning(f"XML文件不存在，跳过: {xml_file}")
            except Exception as e:
                failed_count += 1
                logger.warning(f"清理XML文件失败 {xml_file}: {str(e)}")
        
        logger.info(f"XML清理完成: 删除 {cleaned_count} 个文件, 失败 {failed_count} 个文件")
    
    def cleanup(self):
        """清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {str(e)}")
    
    def extract_dcx_batch(self, dcx_files: List[str], callback=None) -> Dict[str, str]:
        """
        批量多线程解包DCX文件
        
        Args:
            dcx_files: DCX文件路径列表
            callback: 进度回调函数 callback(current, total, filename, status)
            
        Returns:
            {dcx_file: output_dir} 映射字典
        """
        results = {}
        
        def extract_single_dcx(dcx_file: str) -> Tuple[str, str]:
            """解包单个DCX文件"""
            try:
                if callback:
                    callback(0, len(dcx_files), os.path.basename(dcx_file), "开始解包...")
                
                output_dir = self.extract_dcx(dcx_file)
                
                if callback:
                    callback(0, len(dcx_files), os.path.basename(dcx_file), "解包完成")
                    
                return dcx_file, output_dir
            except Exception as e:
                if callback:
                    callback(0, len(dcx_files), os.path.basename(dcx_file), f"解包失败: {str(e)}")
                return dcx_file, ""
        
        logger.info(f"开始批量解包 {len(dcx_files)} 个DCX文件，使用 {self.max_threads} 个线程")
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # 提交所有任务
            future_to_dcx = {executor.submit(extract_single_dcx, dcx_file): dcx_file 
                            for dcx_file in dcx_files}
            
            completed = 0
            # 处理完成的任务
            for future in as_completed(future_to_dcx):
                try:
                    dcx_file, output_dir = future.result()
                    results[dcx_file] = output_dir
                    completed += 1
                    
                    if callback:
                        callback(completed, len(dcx_files), os.path.basename(dcx_file), 
                                "已完成" if output_dir else "失败")
                        
                    logger.info(f"进度: {completed}/{len(dcx_files)} - {os.path.basename(dcx_file)}")
                    
                except Exception as e:
                    dcx_file = future_to_dcx[future]
                    results[dcx_file] = ""
                    completed += 1
                    logger.error(f"解包异常 {os.path.basename(dcx_file)}: {str(e)}")
        
        success_count = len([r for r in results.values() if r])
        logger.info(f"批量解包完成: 成功 {success_count}/{len(dcx_files)}")
        
        return results
    
    def extract_matbin_to_xml_batch(self, matbin_files: List[str], callback=None) -> Dict[str, str]:
        """
        批量多线程转换MATBIN文件为XML（优化版：8线程并发执行批处理）
        
        Args:
            matbin_files: MATBIN文件路径列表
            callback: 进度回调函数
            
        Returns:
            {matbin_file: xml_file} 映射字典
        """
        results = {}
        
        # 将文件分批，每批50个
        batch_size = 50
        batches = [matbin_files[i:i + batch_size] for i in range(0, len(matbin_files), batch_size)]
        
        total_files = len(matbin_files)
        processed_count = 0
        count_lock = threading.Lock() # 用于保护计数器的锁
        
        logger.info(f"开始批量转换 {total_files} 个文件，分 {len(batches)} 批，使用 8 线程并发处理")
        
        def process_batch(batch_index, batch):
            nonlocal processed_count
            batch_results = {}
            try:
                # 执行批处理
                success, error = self._run_witchy_batch(batch, timeout=600)
                
                # 检查结果并更新进度
                for matbin_file in batch:
                    xml_file = matbin_file + '.xml'
                    if os.path.exists(xml_file):
                        batch_results[matbin_file] = xml_file
                    else:
                        batch_results[matbin_file] = ""
                    
                    with count_lock:
                        processed_count += 1
                        current_count = processed_count
                    
                    # 细粒度更新进度（为了平滑性，每个文件都尝试更新，但限制频率防止UI卡顿）
                    # 由于是多线程，这里直接回调即可，UI层通常有如QTimer的机制或者Qt本身的消息队列处理
                    if callback and current_count % 5 == 0: 
                         callback(current_count, total_files, f"处理中... ({current_count}/{total_files})", "转换中")
                
                return batch_results
            except Exception as e:
                logger.error(f"批次 {batch_index} 处理失败: {str(e)}")
                # 标记该批次所有文件失败
                for f in batch:
                    batch_results[f] = ""
                    with count_lock:
                        processed_count += 1
                return batch_results

        # 使用线程池并发处理批次
        # 注意：这里是"批次的并发"，每个批次内部是调用一次WitchyBND
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_batch = {
                executor.submit(process_batch, i, batch): batch 
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(future_to_batch):
                try:
                    batch_res = future.result()
                    results.update(batch_res)
                except Exception as e:
                    logger.error(f"批次任务异常: {str(e)}")

        # 确保最后发送一次100%进度
        if callback:
            callback(total_files, total_files, "转换完成", "完成")
        
        success_count = len([r for r in results.values() if r])
        logger.info(f"批量转换完成: 成功 {success_count}/{total_files} ({(success_count/total_files*100):.1f}%)")
        
        return results
    
    def pack_xml_to_matbin_batch(self, xml_files: List[str], callback=None) -> Dict[str, str]:
        """
        批量转换XML文件为MATBIN（使用拖放方式，串行执行避免冲突）
        
        Args:
            xml_files: XML文件路径列表
            callback: 进度回调函数
            
        Returns:
            {xml_file: matbin_file} 映射字典
        """
        results = {}
        
        logger.info(f"开始批量封包 {len(xml_files)} 个XML文件（串行执行拖放操作）")
        
        # 由于拖放操作可能冲突，使用串行处理
        for i, xml_file in enumerate(xml_files):
            try:
                if callback:
                    callback(i, len(xml_files), os.path.basename(xml_file), "开始封包...")
                
                matbin_file = self.pack_xml_to_matbin(xml_file)
                results[xml_file] = matbin_file
                
                if callback:
                    callback(i + 1, len(xml_files), os.path.basename(xml_file), "封包完成")
                
                logger.info(f"封包进度: {i + 1}/{len(xml_files)} - {os.path.basename(xml_file)}")
                    
            except Exception as e:
                results[xml_file] = ""
                if callback:
                    callback(i + 1, len(xml_files), os.path.basename(xml_file), f"封包失败: {str(e)}")
                logger.error(f"封包失败 {os.path.basename(xml_file)}: {str(e)}")
        
        success_count = len([r for r in results.values() if r])
        logger.info(f"批量封包完成: 成功 {success_count}/{len(xml_files)}")
        
        return results
    
    def __del__(self):
        """析构函数，自动清理"""
        self.cleanup()


class MaterialLibraryImporter:
    """材质库导入器（支持DCX自动解包）- 优化版本"""
    
    def __init__(self, database, witchybnd_path: str = None):
        self.database = database
        self.processor = WitchyBNDProcessor(witchybnd_path)
        # 获取CPU核心数，用于并行处理
        self._max_workers = min(os.cpu_count() or 4, 16)  # 最多使用16个线程
    
    def _parse_single_xml(self, xml_file: str, parser) -> Tuple[Optional[Dict], str, Optional[str]]:
        """
        解析单个XML文件（用于并行处理）
        
        Args:
            xml_file: XML文件路径
            parser: MaterialXMLParser实例
            
        Returns:
            (材质数据, 文件路径, 错误信息) 元组
        """
        try:
            material_data = parser.parse_file(xml_file)
            if material_data:
                return (material_data, xml_file, None)
            else:
                return (None, xml_file, "解析返回空结果")
        except Exception as e:
            return (None, xml_file, str(e))
    
    def import_from_dcx(self, dcx_file: str, library_name: str, description: str = "",
                       progress_callback: Callable[[str, int, int], None] = None) -> Dict[str, any]:
        """
        从DCX文件导入材质库（优化版本：多线程XML解析）
        
        Args:
            dcx_file: DCX文件路径
            library_name: 材质库名称
            description: 材质库描述
            progress_callback: 进度回调函数 (阶段名称, 当前进度, 总数)
            
        Returns:
            导入结果信息
        """
        result = {
            'success': False,
            'library_id': None,
            'material_count': 0,
            'xml_files': [],
            'error': None
        }
        
        def report_progress(stage: str, current: int, total: int):
            """报告进度"""
            if progress_callback:
                try:
                    progress_callback(stage, current, total)
                except Exception:
                    pass
        
        try:
            # 1. 解包DCX文件
            # 传递 total=0 触发UI的忙碌动画
            report_progress("解包DCX文件", 0, 0)
            logger.info(f"开始解包DCX文件: {dcx_file}")
            extracted_dir = self.processor.extract_dcx(dcx_file)
            
            # 2. 批量转换.matbin/.mtd为XML（最耗时的步骤）
            logger.info(f"开始批量转换材质文件(.matbin/.mtd): {extracted_dir}")
            
            # 定义MATBIN转换进度回调
            def matbin_progress(current, total, filename, status=""):
                # 传递实际进度
                report_progress("转换材质文件", current, total)
            
            xml_files = self.processor.batch_extract_matbins(
                extracted_dir, 
                progress_callback=matbin_progress
            )
            result['xml_files'] = xml_files
            
            if not xml_files:
                raise RuntimeError("未找到可转换的材质文件(.matbin/.mtd)")
            
            # 3. 创建材质库
            report_progress("写入数据库", 0, 0)
            library_id = self.database.create_library(
                name=library_name,
                description=description,
                source_path=dcx_file
            )
            result['library_id'] = library_id
            
            # 4. 并行解析XML文件（性能优化关键）
            from .xml_parser import MaterialXMLParser
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            parser = MaterialXMLParser()
            materials_data = []
            successfully_parsed_xml_files = []
            total_files = len(xml_files)
            parsed_count = 0
            
            logger.info(f"开始并行解析 {total_files} 个XML文件（使用 {self._max_workers} 个线程）...")
            report_progress("解析XML文件", 0, total_files)
            
            # 使用线程池并行解析XML
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                # 提交所有解析任务
                future_to_file = {
                    executor.submit(self._parse_single_xml, xml_file, parser): xml_file 
                    for xml_file in xml_files
                }
                
                # 收集结果
                for future in as_completed(future_to_file):
                    parsed_count += 1
                    xml_file = future_to_file[future]
                    report_progress("解析XML文件", parsed_count, total_files)
                    
                    try:
                        material_data, xml_file, error = future.result()
                        if material_data:
                            materials_data.append(material_data)
                            successfully_parsed_xml_files.append(xml_file)
                            logger.debug(f"解析成功: {material_data.get('filename', 'unknown')}")
                        else:
                            logger.warning(f"跳过XML文件 {os.path.basename(xml_file)}: {error}")
                            logger.info(f"保留XML文件以便手动检查: {xml_file}")
                    except Exception as e:
                        xml_file = future_to_file[future]
                        logger.warning(f"跳过XML文件 {os.path.basename(xml_file)}: {str(e)}")
                        logger.info(f"保留XML文件以便手动检查: {xml_file}")
            
            logger.info(f"XML解析完成：成功 {len(materials_data)}/{total_files}")
            
            # 5. 批量添加到数据库（使用优化后的add_materials方法）
            if materials_data:
                total_materials = len(materials_data)
                logger.info(f"开始添加 {total_materials} 个材质到数据库...")
                report_progress("写入数据库", 0, total_materials)
                
                try:
                    # 定义数据库进度回调
                    def db_progress(current, total, message=""):
                        report_progress("写入数据库", current, total)
                    
                    # 使用优化后的批量添加方法
                    if hasattr(self.database, 'add_materials'):
                        self.database.add_materials(
                            library_id, 
                            materials_data,
                            progress_callback=db_progress
                        )
                    else:
                        # 如果没有批量添加方法，逐个添加
                        for i, material_data in enumerate(materials_data):
                            self.database.add_material(library_id, material_data)
                            report_progress("写入数据库", i + 1, total_materials)
                    
                    result['material_count'] = total_materials
                    logger.info(f"成功添加 {total_materials} 个材质到数据库")
                except Exception as e:
                    logger.error(f"添加材质到数据库失败: {str(e)}")
                    result['material_count'] = total_materials
                    result['database_error'] = str(e)
            else:
                logger.warning("没有成功解析的材质数据")
                result['material_count'] = 0
            
            # 6. 清理XML文件，只删除成功解析的文件
            # 6. 清理XML文件，只删除成功解析的文件
            report_progress("清理临时文件", 0, 0)
            logger.info(f"清理成功解析的XML文件 ({len(successfully_parsed_xml_files)}/{len(xml_files)})...")
            if successfully_parsed_xml_files:
                try:
                    self.processor.cleanup_xml_files(successfully_parsed_xml_files)
                    failed_count = len(xml_files) - len(successfully_parsed_xml_files)
                    if failed_count > 0:
                        logger.info(f"保留 {failed_count} 个解析失败的XML文件以便手动检查")
                except Exception as e:
                    logger.warning(f"清理XML文件失败: {str(e)}")
            else:
                logger.warning("没有成功解析的XML文件，保留所有XML文件以便手动检查")
            
            result['success'] = True
            success_msg = f"DCX导入完成: 库ID={library_id}, 材质数量={result['material_count']}"
            if 'database_error' in result:
                success_msg += f" (数据库警告: {result['database_error']})"
            logger.info(success_msg)
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"DCX导入失败: {str(e)}")
        finally:
            # 清理临时目录
            self.processor.cleanup()
        
        return result