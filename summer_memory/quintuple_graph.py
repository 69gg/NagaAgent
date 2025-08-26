import json as _json
from py2neo import Graph, Node, Relationship
import logging
import sys
import os
import time
import uuid

# 添加项目根目录到路径，以便导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 从config模块读取Neo4j配置
try:
    from config import config
    GRAG_ENABLED = config.grag.enabled
    NEO4J_URI = config.grag.neo4j_uri
    NEO4J_USER = config.grag.neo4j_user
    NEO4J_PASSWORD = config.grag.neo4j_password
    NEO4J_DATABASE = config.grag.neo4j_database
    
    try:
        graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), name=NEO4J_DATABASE) if GRAG_ENABLED else None
    except Exception as e:
        print(f"[GRAG] Neo4j连接失败: {e}", file=sys.stderr)
        graph = None
        GRAG_ENABLED = False
except Exception as e:
    print(f"[GRAG] 无法从config模块读取Neo4j配置: {e}", file=sys.stderr)
    # 兼容旧版本，从config.json读取
    try:
        CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _cfg = _json.load(f)
        grag_cfg = _cfg.get('grag', {})
        NEO4J_URI = grag_cfg['neo4j_uri']
        NEO4J_USER = grag_cfg['neo4j_user']
        NEO4J_PASSWORD = grag_cfg['neo4j_password']
        NEO4J_DATABASE = grag_cfg['neo4j_database']
        GRAG_ENABLED = grag_cfg.get('enabled', True)
        try:
            graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), name=NEO4J_DATABASE) if GRAG_ENABLED else None
        except Exception as e:
            print(f"[GRAG] Neo4j连接失败: {e}", file=sys.stderr)
            graph = None
            GRAG_ENABLED = False
    except Exception as e:
        print(f"[GRAG] 无法从 config.json 读取Neo4j配置: {e}", file=sys.stderr)
        graph = None
        GRAG_ENABLED = False

logger = logging.getLogger(__name__)
QUINTUPLES_FILE = "logs/knowledge_graph/quintuples.json"  # 修改为logs目录下的专门文件夹


def load_quintuples():
    """加载增强的五元组数据"""
    try:
        with open(QUINTUPLES_FILE, 'r', encoding='utf-8') as f:
            data = _json.load(f)
            # 兼容旧格式（纯五元组列表）和新格式（增强五元组列表）
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], list):
                    # 旧格式：转换为增强格式
                    enhanced_quintuples = []
                    for quintuple in data:
                        if len(quintuple) == 5:
                            enhanced_quintuples.append({
                                "subject": quintuple[0],
                                "subject_type": quintuple[1],
                                "predicate": quintuple[2],
                                "object": quintuple[3],
                                "object_type": quintuple[4],
                                "timestamp": time.time(),
                                "session_id": str(uuid.uuid4()),
                                "memory_type": "fact",
                                "importance_score": 0.5
                            })
                    return enhanced_quintuples
                elif isinstance(data[0], dict):
                    # 新格式：直接返回
                    return data
        return []
    except FileNotFoundError:
        return []


def save_quintuples(quintuples):
    """保存增强的五元组数据"""
    # 确保目录存在
    import os
    os.makedirs(os.path.dirname(QUINTUPLES_FILE), exist_ok=True)
    
    with open(QUINTUPLES_FILE, 'w', encoding='utf-8') as f:
        _json.dump(quintuples, f, ensure_ascii=False, indent=2)


def store_quintuples(new_quintuples) -> bool:
    """存储增强的五元组到文件和Neo4j，返回是否成功"""
    try:
        from summer_memory.semantic_deduplicator import semantic_deduplicator
        
        all_quintuples = load_quintuples()
        
        # 合并现有五元组和新五元组
        combined_quintuples = all_quintuples + new_quintuples
        
        # 应用语义去重
        deduplicated_quintuples = semantic_deduplicator.smart_deduplicate(combined_quintuples)
        
        # 持久化到文件
        save_quintuples(deduplicated_quintuples)

        # 同步更新Neo4j图谱数据库（仅在GRAG_ENABLED时）
        success = True
        if graph is not None:
            success_count = 0
            for quintuple in new_quintuples:  # 只处理新添加的五元组
                head = quintuple["subject"]
                head_type = quintuple["subject_type"]
                rel = quintuple["predicate"]
                tail = quintuple["object"]
                tail_type = quintuple["object_type"]
                
                if not head or not tail:
                    logger.warning(f"跳过无效五元组，head或tail为空: {quintuple}")
                    continue

                try:
                    # 创建带类型的节点，包含增强信息
                    h_node = Node("Entity", name=head, entity_type=head_type, 
                                 timestamp=quintuple.get("timestamp"), 
                                 memory_type=quintuple.get("memory_type", "fact"),
                                 importance_score=quintuple.get("importance_score", 0.5))
                    t_node = Node("Entity", name=tail, entity_type=tail_type,
                                 timestamp=quintuple.get("timestamp"),
                                 memory_type=quintuple.get("memory_type", "fact"),
                                 importance_score=quintuple.get("importance_score", 0.5))

                    # 创建关系，保存主体和客体类型信息
                    r = Relationship(h_node, rel, t_node, head_type=head_type, tail_type=tail_type,
                                   session_id=quintuple.get("session_id"),
                                   memory_type=quintuple.get("memory_type", "fact"),
                                   importance_score=quintuple.get("importance_score", 0.5))

                    # 合并节点时使用name和entity_type作为唯一标识
                    graph.merge(h_node, "Entity", "name")
                    graph.merge(t_node, "Entity", "name")
                    graph.merge(r)
                    success_count += 1
                except Exception as e:
                    logger.error(f"存储五元组失败: {head}-{rel}-{tail}, 错误: {e}")
                    success = False

            logger.info(f"成功存储 {success_count}/{len(new_quintuples)} 个五元组到Neo4j")
            # 如果至少成功存储了一个五元组，就认为是成功的
            if success_count > 0:
                return True
            else:
                return False
        else:
            logger.info(f"跳过Neo4j存储（未启用），语义去重后保存 {len(deduplicated_quintuples)} 个五元组到文件")
            return True  # 文件存储成功也算成功
    except Exception as e:
        logger.error(f"存储五元组失败: {e}")
        return False

def get_all_quintuples():
    """获取所有增强的五元组"""
    return load_quintuples()


def query_graph_by_keywords(keywords, memory_types=None, importance_threshold=0.0, time_window=None):
    """根据关键词查询增强的五元组"""
    results = []
    if graph is not None:
        for kw in keywords:
            # 构建基础查询
            query = f"""
            MATCH (e1:Entity)-[r]->(e2:Entity)
            WHERE e1.name CONTAINS '{kw}' OR e2.name CONTAINS '{kw}' OR type(r) CONTAINS '{kw}'
               OR e1.entity_type CONTAINS '{kw}' OR e2.entity_type CONTAINS '{kw}'
            """
            
            # 添加记忆类型过滤
            if memory_types:
                memory_types_str = "', '".join(memory_types)
                query += f" AND r.memory_type IN ['{memory_types_str}']"
            
            # 添加重要性阈值过滤
            if importance_threshold > 0:
                query += f" AND r.importance_score >= {importance_threshold}"
            
            # 添加时间窗口过滤
            if time_window:
                current_time = time.time()
                start_time = current_time - time_window
                query += f" AND r.timestamp >= {start_time}"
            
            query += """
            RETURN e1.name, e1.entity_type, type(r), e2.name, e2.entity_type, 
                   r.timestamp, r.session_id, r.memory_type, r.importance_score
            LIMIT 10
            """
            
            res = graph.run(query).data()
            for record in res:
                results.append({
                    "subject": record['e1.name'],
                    "subject_type": record['e1.entity_type'],
                    "predicate": record['type(r)'],
                    "object": record['e2.name'],
                    "object_type": record['e2.entity_type'],
                    "timestamp": record.get('r.timestamp'),
                    "session_id": record.get('r.session_id'),
                    "memory_type": record.get('r.memory_type', 'fact'),
                    "importance_score": record.get('r.importance_score', 0.5)
                })
    
    return results


def query_quintuples_by_keywords(keywords, memory_types=None, importance_threshold=0.0, time_window=None):
    """从文件中查询增强的五元组"""
    from summer_memory.time_axis_manager import time_axis_manager
    
    all_quintuples = load_quintuples()
    
    # 应用时间窗口过滤
    if time_window:
        all_quintuples = time_axis_manager.filter_by_time_window(all_quintuples, time_window)
    
    results = []
    
    for quintuple in all_quintuples:
        # 检查关键词匹配
        matched = False
        for kw in keywords:
            if (kw in quintuple["subject"] or kw in quintuple["subject_type"] or
                kw in quintuple["predicate"] or kw in quintuple["object"] or 
                kw in quintuple["object_type"]):
                matched = True
                break
        
        if not matched:
            continue
        
        # 检查记忆类型过滤
        if memory_types and quintuple.get("memory_type", "fact") not in memory_types:
            continue
        
        # 检查重要性阈值（使用时间衰减后的重要性）
        decayed_importance = time_axis_manager.apply_time_decay(quintuple)
        if importance_threshold > 0 and decayed_importance < importance_threshold:
            continue
        
        # 添加衰减后的重要性分数
        quintuple_with_decay = quintuple.copy()
        quintuple_with_decay["decayed_importance"] = decayed_importance
        
        results.append(quintuple_with_decay)
    
    return results


def get_memory_timeline(keywords=None, memory_types=None, time_window=None):
    """获取记忆时间线"""
    from summer_memory.time_axis_manager import time_axis_manager
    
    all_quintuples = load_quintuples()
    
    # 应用关键词过滤
    if keywords:
        filtered_quintuples = []
        for quintuple in all_quintuples:
            matched = False
            for kw in keywords:
                if (kw in quintuple["subject"] or kw in quintuple["subject_type"] or
                    kw in quintuple["predicate"] or kw in quintuple["object"] or 
                    kw in quintuple["object_type"]):
                    matched = True
                    break
            if matched:
                filtered_quintuples.append(quintuple)
        all_quintuples = filtered_quintuples
    
    # 应用记忆类型过滤
    if memory_types:
        all_quintuples = [q for q in all_quintuples if q.get("memory_type", "fact") in memory_types]
    
    # 获取时间线
    return time_axis_manager.get_memory_timeline(all_quintuples, time_window)


def get_recent_quintuples(hours=24, memory_types=None):
    """获取最近N小时内的五元组"""
    from summer_memory.time_axis_manager import time_axis_manager
    
    all_quintuples = load_quintuples()
    recent_quintuples = time_axis_manager.get_recent_quintuples(all_quintuples, hours)
    
    # 应用记忆类型过滤
    if memory_types:
        recent_quintuples = [q for q in recent_quintuples if q.get("memory_type", "fact") in memory_types]
    
    return recent_quintuples


def analyze_temporal_patterns():
    """分析记忆的时间模式"""
    from summer_memory.time_axis_manager import time_axis_manager
    
    all_quintuples = load_quintuples()
    return time_axis_manager.analyze_temporal_patterns(all_quintuples)


def analyze_similarity_patterns():
    """分析记忆的相似度模式"""
    from summer_memory.semantic_deduplicator import semantic_deduplicator
    
    all_quintuples = load_quintuples()
    return semantic_deduplicator.analyze_similarity_patterns(all_quintuples)


def get_similarity_groups():
    """获取相似度分组"""
    from summer_memory.semantic_deduplicator import semantic_deduplicator
    
    all_quintuples = load_quintuples()
    return semantic_deduplicator.group_by_similarity(all_quintuples)


def deduplicate_existing_quintuples():
    """对现有五元组进行去重"""
    from summer_memory.semantic_deduplicator import semantic_deduplicator
    
    all_quintuples = load_quintuples()
    deduplicated = semantic_deduplicator.smart_deduplicate(all_quintuples)
    
    # 保存去重后的结果
    save_quintuples(deduplicated)
    
    logger.info(f"现有五元组去重: {len(all_quintuples)} -> {len(deduplicated)}")
    return deduplicated