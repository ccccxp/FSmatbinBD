#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XML解析器 - 用于解析材质配置XML文件
"""

import xml.etree.ElementTree as ET
import os
from typing import Dict, List, Any, Optional, Tuple
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MaterialXMLParser:
    """材质XML文件解析器"""
    
    def __init__(self):
        self.supported_extensions = ['.xml']
    
    def parse_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """
        解析目录下的所有XML材质文件
        
        Args:
            directory_path: 目录路径
            
        Returns:
            解析后的材质数据列表
        """
        materials = []
        
        if not os.path.exists(directory_path):
            logger.error(f"目录不存在: {directory_path}")
            return materials
        
        # 遍历目录及子目录
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.supported_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        material_data = self.parse_file(file_path)
                        if material_data:
                            materials.append(material_data)
                            logger.info(f"成功解析文件: {file}")
                    except Exception as e:
                        logger.error(f"解析文件失败 {file}: {str(e)}")
                        continue
        
        logger.info(f"共解析 {len(materials)} 个材质文件")
        return materials
    
    def parse_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        解析单个XML材质文件
        支持新版本MATBIN格式和老版本MTD格式
        
        Args:
            file_path: XML文件路径
            
        Returns:
            解析后的材质数据字典
        """
        try:
            # 解析XML文件
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 检查格式：支持MATBIN（新版本）和MTD（老版本）
            is_mtd_format = (root.tag == 'MTD')
            is_matbin_format = (root.tag == 'MATBIN')
            
            if not (is_mtd_format or is_matbin_format):
                logger.warning(f"文件 {file_path} 格式不支持（根标签：{root.tag}）")
                return None
            
            # 提取基本信息
            material_data = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'filename': self._get_element_text(root, 'filename', ''),
                'shader_path': self._get_element_text(root, 'ShaderPath', ''),
                'source_path': self._get_element_text(root, 'SourcePath', ''),
                'compression': self._get_element_text(root, 'compression', ''),
                'key': self._get_element_text(root, 'Key', ''),  # 老版本MTD可能没有Key
                'description': self._get_element_text(root, 'Description', '') if is_mtd_format else '',  # MTD格式特有
                'is_mtd_format': is_mtd_format,  # 标记格式类型
                'params': self._parse_params(root),
                'samplers': self._parse_samplers(root) if is_matbin_format else self._parse_textures(root)
            }
            
            # 如果是MTD格式且没有Key，可以从文件名生成一个标识
            if is_mtd_format and not material_data['key']:
                # 老版本MTD文件没有Key字段，这是正常的
                material_data['key'] = ''
            
            return material_data
            
        except ET.ParseError as e:
            logger.error(f"XML解析错误 {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"文件处理错误 {file_path}: {str(e)}")
            return None
    
    def _get_element_text(self, parent: ET.Element, tag: str, default: str = '') -> str:
        """获取XML元素的文本内容"""
        element = parent.find(tag)
        return element.text if element is not None and element.text else default
    
    def _parse_params(self, root: ET.Element) -> List[Dict[str, Any]]:
        """解析材质参数"""
        params = []
        params_element = root.find('Params')
        
        if params_element is None:
            return params
        
        for param in params_element.findall('Param'):
            try:
                param_data = {
                    'name': self._get_element_text(param, 'Name'),
                    'type': self._get_element_text(param, 'Type'),
                    'key': self._get_element_text(param, 'Key'),
                    'value': self._parse_param_value(param)
                }
                params.append(param_data)
            except Exception as e:
                logger.warning(f"解析参数失败: {str(e)}")
                continue
        
        return params
    
    def _parse_param_value(self, param: ET.Element) -> Any:
        """解析参数值"""
        value_element = param.find('Value')
        if value_element is None:
            return None
        
        param_type = self._get_element_text(param, 'Type', 'String').lower()
        
        try:
            # 根据参数类型解析值
            if param_type == 'bool':
                return value_element.text.lower() == 'true' if value_element.text else False
            elif param_type == 'int':
                return int(value_element.text) if value_element.text else 0
            elif param_type == 'float':
                return float(value_element.text) if value_element.text else 0.0
            elif param_type in ['int2', 'float2', 'float3', 'float4', 'float5']:
                # 处理数组类型 - 支持ArrayOfInt和ArrayOfFloat
                if param_type.startswith('int'):
                    # Int数组：查找<int>元素
                    int_elements = value_element.findall('int')
                    if int_elements:
                        return [int(elem.text) if elem.text else 0 for elem in int_elements]
                else:
                    # Float数组：查找<float>元素
                    float_elements = value_element.findall('float')
                    if float_elements:
                        return [float(elem.text) if elem.text else 0.0 for elem in float_elements]
                
                # 如果没有找到对应元素，尝试解析文本内容
                if value_element.text and value_element.text.strip():
                    try:
                        # 尝试解析逗号分隔的值
                        values = [x.strip() for x in value_element.text.split(',') if x.strip()]
                        if param_type.startswith('int'):
                            return [int(float(x)) for x in values]
                        else:
                            return [float(x) for x in values]
                    except (ValueError, TypeError):
                        pass
                
                # 返回空数组作为默认值
                return []
            else:
                # 默认作为字符串处理
                return value_element.text if value_element.text else ''
                
        except (ValueError, TypeError) as e:
            logger.warning(f"参数值解析失败: {str(e)}")
            return value_element.text if value_element.text else ''
    
    def _parse_samplers(self, root: ET.Element) -> List[Dict[str, Any]]:
        """解析材质样例（新版本MATBIN格式）"""
        samplers = []
        samplers_element = root.find('Samplers')
        
        if samplers_element is None:
            return samplers
        
        for sampler in samplers_element.findall('Sampler'):
            try:
                sampler_data = {
                    'type': self._get_element_text(sampler, 'Type'),
                    'path': self._get_element_text(sampler, 'Path'),
                    'key': self._get_element_text(sampler, 'Key'),
                    'unk14': self._parse_unk14(sampler)
                }
                samplers.append(sampler_data)
            except Exception as e:
                logger.warning(f"解析样例失败: {str(e)}")
                continue
        
        return samplers
    
    def _parse_textures(self, root: ET.Element) -> List[Dict[str, Any]]:
        """解析纹理数据（老版本MTD格式）"""
        textures = []
        textures_element = root.find('Textures')
        
        if textures_element is None:
            return textures
        
        for texture in textures_element.findall('Texture'):
            try:
                # 解析UnkFloats
                unk_floats = {'X': 0, 'Y': 0}
                unk_floats_element = texture.find('UnkFloats')
                if unk_floats_element is not None:
                    float_elements = unk_floats_element.findall('float')
                    if len(float_elements) >= 2:
                        try:
                            unk_floats['X'] = int(float(float_elements[0].text)) if float_elements[0].text else 0
                            unk_floats['Y'] = int(float(float_elements[1].text)) if float_elements[1].text else 0
                        except (ValueError, TypeError):
                            pass
                
                # MTD格式的Texture转换为Sampler格式以保持兼容性
                texture_data = {
                    'type': self._get_element_text(texture, 'Type'),
                    'path': self._get_element_text(texture, 'Path'),
                    'key': '',  # MTD格式的Texture没有Key字段
                    'unk14': unk_floats,  # 使用UnkFloats作为unk14
                    # 额外保存MTD特有字段
                    'extended': self._get_element_text(texture, 'Extended', 'false').lower() == 'true',
                    'uv_number': int(self._get_element_text(texture, 'UVNumber', '0')),
                    'shader_data_index': int(self._get_element_text(texture, 'ShaderDataIndex', '0'))
                }
                textures.append(texture_data)
            except Exception as e:
                logger.warning(f"解析纹理失败: {str(e)}")
                continue
        
        return textures
    
    def _parse_unk14(self, sampler: ET.Element) -> Dict[str, int]:
        """解析Unk14元素"""
        unk14_element = sampler.find('Unk14')
        if unk14_element is None:
            return {'X': 0, 'Y': 0}
        
        try:
            return {
                'X': int(self._get_element_text(unk14_element, 'X', '0')),
                'Y': int(self._get_element_text(unk14_element, 'Y', '0'))
            }
        except ValueError:
            return {'X': 0, 'Y': 0}
    
    def export_material_to_xml(self, material_data: Dict[str, Any], output_path: str) -> bool:
        """
        导出材质数据为XML文件
        支持新版本MATBIN格式和老版本MTD格式
        
        Args:
            material_data: 材质数据字典
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            # 判断是否为MTD格式 - 优先使用is_mtd_format标记，否则从文件名检测
            is_mtd_format = material_data.get('is_mtd_format', False)
            
            # 如果没有明确指定，从文件名推断格式
            if not is_mtd_format:
                filename = material_data.get('filename', '')
                if filename.lower().endswith('.mtd'):
                    is_mtd_format = True
                    logger.info(f"从文件名检测到MTD格式: {filename}")
            
            # 创建根元素
            root = ET.Element('MTD' if is_mtd_format else 'MATBIN')
            root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            root.set('xmlns:xsd', 'http://www.w3.org/2001/XMLSchema')
            root.set('WitchyVersion', '2150000')
            
            # 添加基本信息
            ET.SubElement(root, 'filename').text = material_data.get('filename', '')
            ET.SubElement(root, 'compression').text = material_data.get('compression', 'None')
            ET.SubElement(root, 'ShaderPath').text = material_data.get('shader_path', '')
            
            # MTD格式可能有Description字段
            if is_mtd_format:
                description = material_data.get('description', '')
                if description:
                    ET.SubElement(root, 'Description').text = description
            else:
                # MATBIN格式有SourcePath
                ET.SubElement(root, 'SourcePath').text = material_data.get('source_path', '')
            
            # 只有MATBIN格式有Key字段，MTD格式没有
            if not is_mtd_format:
                material_key = (material_data.get('key_value', '') or 
                              material_data.get('material_key', '') or 
                              material_data.get('Key', '') or 
                              material_data.get('key', ''))
                ET.SubElement(root, 'Key').text = str(material_key) if material_key else ''
            
            # 添加参数（保持原始顺序）
            if material_data.get('params'):
                params_element = ET.SubElement(root, 'Params')
                for param in material_data['params']:
                    param_element = ET.SubElement(params_element, 'Param')
                    ET.SubElement(param_element, 'Name').text = param.get('name', '')
                    
                    # 添加Value元素
                    value_element = ET.SubElement(param_element, 'Value')
                    param_type = param.get('type', 'String')
                    param_value = param.get('value')
                    
                    # 根据类型设置xsi:type属性和值
                    if param_type.lower() == 'bool':
                        value_element.set('xsi:type', 'xsd:boolean')
                        # Bool值确保为小写的true/false
                        if isinstance(param_value, str):
                            bool_val = param_value.lower()
                            value_element.text = bool_val if bool_val in ['true', 'false'] else 'false'
                        else:
                            value_element.text = 'true' if param_value else 'false'
                    elif param_type.lower() == 'int':
                        value_element.set('xsi:type', 'xsd:int')
                        try:
                            value_element.text = str(int(float(param_value))) if param_value is not None else '0'
                        except (ValueError, TypeError):
                            value_element.text = '0'
                    elif param_type.lower() == 'float':
                        value_element.set('xsi:type', 'xsd:float')
                        try:
                            if param_value is not None:
                                float_val = float(param_value)
                                # 优化数字格式：1.0 -> 1, 2.0 -> 2
                                if float_val == int(float_val):
                                    value_element.text = str(int(float_val))
                                else:
                                    value_element.text = str(float_val)
                            else:
                                value_element.text = '0'
                        except (ValueError, TypeError):
                            value_element.text = '0'
                    elif param_type.lower() in ['int2', 'float2', 'float3', 'float4', 'float5']:
                        # 数组类型：按照原始格式导出
                        if param_type.lower().startswith('int'):
                            value_element.set('xsi:type', 'ArrayOfInt')
                            element_tag = 'int'
                        else:
                            value_element.set('xsi:type', 'ArrayOfFloat')
                            element_tag = 'float'
                        
                        # 处理数组值
                        if isinstance(param_value, list):
                            # 如果是解析后的数值列表（从材质面板返回）
                            for val in param_value:
                                try:
                                    if element_tag == 'int':
                                        int_val = int(float(val))
                                        ET.SubElement(value_element, element_tag).text = str(int_val)
                                    else:
                                        float_val = float(val)
                                        # 优化数字格式：1.0 -> 1, 2.0 -> 2
                                        if float_val == int(float_val):
                                            ET.SubElement(value_element, element_tag).text = str(int(float_val))
                                        else:
                                            ET.SubElement(value_element, element_tag).text = str(float_val)
                                except (ValueError, TypeError):
                                    ET.SubElement(value_element, element_tag).text = '0' if element_tag == 'int' else '0'
                        elif isinstance(param_value, str):
                            # 如果是字符串格式 "[1.0, 2.0, 3.0]" 或 "1.0, 2.0, 3.0"
                            array_str = param_value.strip()
                            
                            # 处理带括号的格式
                            if array_str.startswith('[') and array_str.endswith(']'):
                                inner = array_str[1:-1].strip()
                            else:
                                inner = array_str
                            
                            if inner:
                                # 分割并处理每个值
                                values = [x.strip() for x in inner.split(',') if x.strip()]
                                for val in values:
                                    try:
                                        if element_tag == 'int':
                                            int_val = int(float(val))
                                            ET.SubElement(value_element, element_tag).text = str(int_val)
                                        else:
                                            float_val = float(val)
                                            # 优化数字格式：1.0 -> 1, 2.0 -> 2
                                            if float_val == int(float_val):
                                                ET.SubElement(value_element, element_tag).text = str(int(float_val))
                                            else:
                                                ET.SubElement(value_element, element_tag).text = str(float_val)
                                    except (ValueError, TypeError):
                                        ET.SubElement(value_element, element_tag).text = '0' if element_tag == 'int' else '0'
                            else:
                                # 空数组，添加默认值
                                ET.SubElement(value_element, element_tag).text = '0'
                        else:
                            # 其他情况，添加默认值
                            ET.SubElement(value_element, element_tag).text = '0'
                    else:
                        # 其他类型（String等）
                        value_element.text = str(param_value) if param_value is not None else ''
                    
                    # MTD格式没有参数的Key字段
                    if not is_mtd_format:
                        key_value = param.get('key_value', '') or param.get('key', '')
                        ET.SubElement(param_element, 'Key').text = str(key_value) if key_value else ''
                    ET.SubElement(param_element, 'Type').text = param_type
            
            # 添加样例/纹理
            if material_data.get('samplers'):
                # 判断使用Samplers还是Textures
                if is_mtd_format:
                    # MTD格式：使用Textures
                    textures_element = ET.SubElement(root, 'Textures')
                    for sampler in material_data['samplers']:
                        texture_element = ET.SubElement(textures_element, 'Texture')
                        ET.SubElement(texture_element, 'Type').text = sampler.get('type', '')
                        
                        # MTD特有字段
                        extended = sampler.get('extended', True)
                        ET.SubElement(texture_element, 'Extended').text = 'true' if extended else 'false'
                        ET.SubElement(texture_element, 'UVNumber').text = str(sampler.get('uv_number', 1))
                        ET.SubElement(texture_element, 'ShaderDataIndex').text = str(sampler.get('shader_data_index', 0))
                        
                        ET.SubElement(texture_element, 'Path').text = sampler.get('path', '')
                        
                        # MTD使用UnkFloats而不是Unk14
                        unk14_x = 0
                        unk14_y = 0
                        if isinstance(sampler.get('unk14'), dict):
                            unk14_data = sampler.get('unk14', {'X': 0, 'Y': 0})
                            unk14_x = unk14_data.get('X', 0)
                            unk14_y = unk14_data.get('Y', 0)
                        else:
                            unk14_x = sampler.get('unk14_x', 0)
                            unk14_y = sampler.get('unk14_y', 0)
                        
                        unk_floats_element = ET.SubElement(texture_element, 'UnkFloats')
                        ET.SubElement(unk_floats_element, 'float').text = str(unk14_x)
                        ET.SubElement(unk_floats_element, 'float').text = str(unk14_y)
                else:
                    # MATBIN格式：使用Samplers
                    samplers_element = ET.SubElement(root, 'Samplers')
                    for sampler in material_data['samplers']:
                        sampler_element = ET.SubElement(samplers_element, 'Sampler')
                        ET.SubElement(sampler_element, 'Type').text = sampler.get('type', '')
                        ET.SubElement(sampler_element, 'Path').text = sampler.get('path', '')
                        # 修复：使用正确的键字段名
                        key_value = sampler.get('key_value', '') or sampler.get('key', '')
                        ET.SubElement(sampler_element, 'Key').text = str(key_value) if key_value else ''
                        
                        # 添加Unk14
                        unk14_x = sampler.get('unk14_x', 0)
                        unk14_y = sampler.get('unk14_y', 0)
                        # 兼容新旧数据格式
                        if isinstance(sampler.get('unk14'), dict):
                            unk14_data = sampler.get('unk14', {'X': 0, 'Y': 0})
                            unk14_x = unk14_data.get('X', 0)
                            unk14_y = unk14_data.get('Y', 0)
                        
                        unk14_element = ET.SubElement(sampler_element, 'Unk14')
                        ET.SubElement(unk14_element, 'X').text = str(unk14_x)
                        ET.SubElement(unk14_element, 'Y').text = str(unk14_y)
            
            # 格式化并写入文件
            self._indent_xml(root)
            tree = ET.ElementTree(root)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 写入文件，添加XML声明
            with open(output_path, 'wb') as f:
                f.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
                tree.write(f, encoding='utf-8', xml_declaration=False)
            
            logger.info(f"材质导出成功: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"材质导出失败: {str(e)}")
            return False
    
    def _indent_xml(self, elem: ET.Element, level: int = 0):
        """格式化XML缩进"""
        indent = "  "
        if len(elem) > 0:
            if not elem.text or not elem.text.strip():
                elem.text = f"\n{indent * (level + 1)}"
            if not elem.tail or not elem.tail.strip():
                elem.tail = f"\n{indent * level}"
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = f"\n{indent * level}"
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = f"\n{indent * level}"


class XMLParser:
    """MATBIN材质XML文件解析器"""
    
    def __init__(self):
        """初始化XML解析器"""
        pass
    
    def parse_matbin_xml(self, xml_file: str) -> Dict[str, Any]:
        """
        解析MATBIN的XML文件
        
        Args:
            xml_file: XML文件路径
            
        Returns:
            解析后的材质数据字典
        """
        try:
            if not os.path.exists(xml_file):
                raise FileNotFoundError(f"XML文件不存在: {xml_file}")
            
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # 基础材质数据结构
            material_data = {
                'filename': os.path.basename(xml_file),
                'root_tag': root.tag,
                'attributes': root.attrib.copy(),
                'textures': [],
                'parameters': {},
                'shaders': [],
                'properties': {}
            }
            
            # 解析纹理信息
            for texture_elem in root.findall('.//texture'):
                texture_info = {
                    'name': texture_elem.get('name', ''),
                    'path': texture_elem.get('path', ''),
                    'type': texture_elem.get('type', ''),
                    'attributes': texture_elem.attrib.copy()
                }
                material_data['textures'].append(texture_info)
            
            # 解析材质参数
            for param_elem in root.findall('.//parameter'):
                param_name = param_elem.get('name', '')
                param_value = param_elem.get('value', '')
                param_type = param_elem.get('type', 'string')
                
                material_data['parameters'][param_name] = {
                    'value': param_value,
                    'type': param_type,
                    'attributes': param_elem.attrib.copy()
                }
            
            # 解析着色器信息
            for shader_elem in root.findall('.//shader'):
                shader_info = {
                    'name': shader_elem.get('name', ''),
                    'type': shader_elem.get('type', ''),
                    'attributes': shader_elem.attrib.copy()
                }
                material_data['shaders'].append(shader_info)
            
            # 解析其他属性
            for prop_elem in root.findall('.//*'):
                if prop_elem.tag not in ['texture', 'parameter', 'shader']:
                    prop_name = prop_elem.tag
                    if prop_name not in material_data['properties']:
                        material_data['properties'][prop_name] = []
                    
                    prop_data = {
                        'text': prop_elem.text,
                        'attributes': prop_elem.attrib.copy(),
                        'children': len(list(prop_elem))
                    }
                    material_data['properties'][prop_name].append(prop_data)
            
            logger.debug(f"XML解析完成: {xml_file}")
            return material_data
            
        except ET.ParseError as e:
            logger.error(f"XML解析错误: {xml_file} - {str(e)}")
            raise
        except Exception as e:
            logger.error(f"XML文件解析失败: {xml_file} - {str(e)}")
            raise
    
    def extract_material_info(self, xml_file: str) -> Dict[str, str]:
        """
        提取材质的基本信息
        
        Args:
            xml_file: XML文件路径
            
        Returns:
            材质基本信息字典
        """
        try:
            material_data = self.parse_matbin_xml(xml_file)
            
            # 提取关键信息
            info = {
                'filename': material_data.get('filename', ''),
                'material_name': os.path.splitext(material_data.get('filename', ''))[0],
                'texture_count': len(material_data.get('textures', [])),
                'parameter_count': len(material_data.get('parameters', {})),
                'shader_count': len(material_data.get('shaders', [])),
                'root_tag': material_data.get('root_tag', 'unknown'),
            }
            
            # 提取主要纹理路径
            textures = material_data.get('textures', [])
            if textures:
                info['primary_texture'] = textures[0].get('path', '')
                info['texture_names'] = [t.get('name', '') for t in textures]
            else:
                info['primary_texture'] = ''
                info['texture_names'] = []
            
            # 提取着色器信息
            shaders = material_data.get('shaders', [])
            if shaders:
                info['primary_shader'] = shaders[0].get('name', '')
                info['shader_names'] = [s.get('name', '') for s in shaders]
            else:
                info['primary_shader'] = ''
                info['shader_names'] = []
            
            return info
            
        except Exception as e:
            logger.error(f"提取材质信息失败: {xml_file} - {str(e)}")
            return {
                'filename': os.path.basename(xml_file),
                'material_name': os.path.splitext(os.path.basename(xml_file))[0],
                'error': str(e)
            }
    
    def validate_xml(self, xml_file: str) -> bool:
        """
        验证XML文件格式是否正确
        
        Args:
            xml_file: XML文件路径
            
        Returns:
            是否为有效的XML文件
        """
        try:
            if not os.path.exists(xml_file):
                return False
            
            # 尝试解析XML
            ET.parse(xml_file)
            return True
            
        except ET.ParseError:
            logger.warning(f"XML格式错误: {xml_file}")
            return False
        except Exception:
            logger.warning(f"XML文件读取失败: {xml_file}")
            return False