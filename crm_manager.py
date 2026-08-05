"""
CRM客户管理系统 - 核心业务逻辑
仿照weather_api.py的面向对象设计
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
import json
from pathlib import Path

class CRMError(Exception):
    """自定义异常类 - 处理CRM相关错误"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
    
    def __str__(self):
        if self.status_code:
            return f"{self.message} (状态码: {self.status_code})"
        return self.message

class ClientManager:
    """
    CRM客户管理类
    封装所有客户和跟进记录的操作
    """
    
    def __init__(self, db_path: str = "crm.db"):
        """初始化CRM管理器"""
        print("=== 初始化CRM系统 ===")
        
        self.db_path = db_path
        self.init_database()
        print(f"✅ CRM系统初始化成功")
        print(f"   数据库: {self.db_path}")
    
    def init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建客户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    company TEXT,
                    phone TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建跟进记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    next_date DATE NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            raise CRMError(f"数据库初始化失败: {e}")
    
    def add_client(self, name: str, company: str = "", phone: str = "", email: str = "") -> Dict:
        """添加新客户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO clients (name, company, phone, email)
                VALUES (?, ?, ?, ?)
            ''', (name, company, phone, email))
            
            client_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "id": client_id,
                "name": name,
                "company": company,
                "phone": phone,
                "email": email
            }
            
        except sqlite3.Error as e:
            raise CRMError(f"添加客户失败: {e}")
    
    def get_all_clients(self) -> List[Dict]:
        """获取所有客户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.*, 
                       (SELECT COUNT(*) FROM followups f WHERE f.client_id = c.id) as followup_count,
                       (SELECT MAX(next_date) FROM followups f WHERE f.client_id = c.id) as last_followup
                FROM clients c
                ORDER BY c.created_at DESC
            ''')
            
            clients = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                client = dict(zip(columns, row))
                clients.append(client)
            
            conn.close()
            return clients
            
        except sqlite3.Error as e:
            raise CRMError(f"获取客户列表失败: {e}")
    
    def add_followup(self, client_id: int, note: str, next_date: date) -> Dict:
        """添加跟进记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查客户是否存在
            cursor.execute('SELECT id FROM clients WHERE id = ?', (client_id,))
            if not cursor.fetchone():
                raise CRMError(f"客户ID {client_id} 不存在")
            
            # 插入跟进记录
            cursor.execute('''
                INSERT INTO followups (client_id, note, next_date)
                VALUES (?, ?, ?)
            ''', (client_id, note, next_date))
            
            followup_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "id": followup_id,
                "client_id": client_id,
                "note": note,
                "next_date": next_date
            }
            
        except sqlite3.Error as e:
            raise CRMError(f"添加跟进记录失败: {e}")
    
    def get_upcoming_followups(self, days: int = 7) -> List[Dict]:
        """获取即将到期的跟进记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT f.*, c.name as client_name, c.company
                FROM followups f
                JOIN clients c ON f.client_id = c.id
                WHERE f.next_date BETWEEN date('now') AND date('now', ?)
                AND f.status = 'pending'
                ORDER BY f.next_date ASC
            ''', (f'+{days} days',))
            
            followups = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                followup = dict(zip(columns, row))
                followups.append(followup)
            
            conn.close()
            return followups
            
        except sqlite3.Error as e:
            raise CRMError(f"获取跟进记录失败: {e}")
    
    def get_client_stats(self) -> Dict:
        """获取客户统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 客户总数
            cursor.execute('SELECT COUNT(*) FROM clients')
            total_clients = cursor.fetchone()[0]
            
            # 本周需要跟进的客户数
            cursor.execute('''
                SELECT COUNT(DISTINCT client_id) 
                FROM followups 
                WHERE next_date BETWEEN date('now') AND date('now', '+7 days')
                AND status = 'pending'
            ''')
            upcoming_followups = cursor.fetchone()[0]
            
            # 按公司分类
            cursor.execute('''
                SELECT company, COUNT(*) as count 
                FROM clients 
                WHERE company != '' 
                GROUP BY company 
                ORDER BY count DESC
                LIMIT 5
            ''')
            companies = cursor.fetchall()
            
            conn.close()
            
            return {
                "total_clients": total_clients,
                "upcoming_followups": upcoming_followups,
                "top_companies": [{"name": c[0], "count": c[1]} for c in companies]
            }
            
        except sqlite3.Error as e:
            raise CRMError(f"获取统计信息失败: {e}")
    
    def delete_client(self, client_id: int) -> bool:
        """删除客户及其跟进记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 先删除跟进记录
            cursor.execute('DELETE FROM followups WHERE client_id = ?', (client_id,))
            
            # 再删除客户
            cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected_rows > 0
            
        except sqlite3.Error as e:
            raise CRMError(f"删除客户失败: {e}")

# 测试代码
if __name__ == "__main__":
    print("🧪 测试CRM系统...")
    
    try:
        crm = ClientManager()
        
        # 添加测试数据
        print("\n1. 添加测试客户...")
        client1 = crm.add_client("张三", "腾讯科技", "13800138000", "zhangsan@example.com")
        print(f"   添加成功: {client1['name']} (ID: {client1['id']})")
        
        client2 = crm.add_client("李四", "阿里巴巴", "13900139000", "lisi@example.com")
        print(f"   添加成功: {client2['name']} (ID: {client2['id']})")
        
        # 添加跟进记录
        print("\n2. 添加跟进记录...")
        followup1 = crm.add_followup(client1['id'], "电话沟通，对产品A感兴趣", date(2024, 3, 28))
        print(f"   跟进记录添加成功: {followup1['note']}")
        
        followup2 = crm.add_followup(client2['id'], "发送了产品资料，等待回复", date(2024, 3, 25))
        print(f"   跟进记录添加成功: {followup2['note']}")
        
        # 获取客户列表
        print("\n3. 获取客户列表...")
        clients = crm.get_all_clients()
        print(f"   共有 {len(clients)} 个客户:")
        for client in clients:
            print(f"   - {client['name']} ({client['company']})")
        
        # 获取统计信息
        print("\n4. 获取统计信息...")
        stats = crm.get_client_stats()
        print(f"   客户总数: {stats['total_clients']}")
        print(f"   本周需要跟进: {stats['upcoming_followups']} 个客户")
        
        print("\n✅ 测试完成！CRM系统运行正常")
        
    except CRMError as e:
        print(f"❌ 测试失败: {e}")
