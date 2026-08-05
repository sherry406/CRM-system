"""
CRM客户跟进系统 - 主程序
使用FastAPI搭建Web应用
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import date
import uvicorn
import os
from dotenv import load_dotenv

# 导入我们的CRM管理器
from crm_manager import ClientManager, CRMError

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="CRM客户跟进系统",
    description="简易客户关系管理系统",
    version="1.0.0"
)

# 设置模板和静态文件目录
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建CRM管理器实例
crm = ClientManager()

# ========== 路由定义 ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页 - 显示客户列表和统计信息"""
    try:
        # 获取数据
        clients = crm.get_all_clients()
        upcoming = crm.get_upcoming_followups(days=7)
        stats = crm.get_client_stats()
        
        # 渲染模板
        return templates.TemplateResponse("index.html", {
            "request": request,
            "clients": clients,
            "upcoming": upcoming,
            "stats": stats,
            "today": date.today().strftime("%Y-%m-%d")
        })
        
    except CRMError as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": str(e)
        })

@app.post("/add_client")
async def add_client(
    request: Request,
    name: str = Form(...),
    company: str = Form(""),
    phone: str = Form(""),
    email: str = Form("")
):
    """添加新客户"""
    try:
        crm.add_client(name, company, phone, email)
        return RedirectResponse(url="/", status_code=303)
        
    except CRMError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/add_followup")
async def add_followup(
    request: Request,
    client_id: int = Form(...),
    note: str = Form(...),
    next_date: date = Form(...)
):
    """添加跟进记录"""
    try:
        crm.add_followup(client_id, note, next_date)
        return RedirectResponse(url="/", status_code=303)
        
    except CRMError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/delete_client/{client_id}")
async def delete_client(client_id: int):
    """删除客户"""
    try:
        if crm.delete_client(client_id):
            return RedirectResponse(url="/", status_code=303)
        else:
            raise HTTPException(status_code=404, detail="客户不存在")
            
    except CRMError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """获取统计数据（API接口）"""
    try:
        return crm.get_client_stats()
    except CRMError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "CRM System"}

# ========== 启动应用 ==========
if __name__ == "__main__":
    print(f"🚀 启动CRM系统...")
    print(f"   应用名称: {os.getenv('APP_NAME', 'CRM系统')}")
    print(f"   版本: {os.getenv('APP_VERSION', '1.0.0')}")
    print(f"   访问地址: http://localhost:8001")
    print(f"   API文档: http://localhost:8001/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        reload=False  # 开发模式，代码修改自动重启
    )
