from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.core.logger import get_main_logger
from app.core.security import verify_auth_token
from app.services.key_manager import get_key_manager_instance
from app.core.config import settings
from app.api import gemini_routes, openai_routes, claude_routes
import uvicorn


# 配置日志
logger = get_main_logger()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# 配置Jinja2模板
templates = Jinja2Templates(directory="app/templates")

# 配置静态文件
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 创建 KeyManager 实例
key_manager = None

@app.on_event("startup")
async def startup_event():
    global key_manager
    logger.info("Application starting up...")
    try:
        key_manager = await get_key_manager_instance(settings.API_KEYS)
        logger.info("KeyManager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize KeyManager: {str(e)}")
        raise

# 添加中间件来处理未经身份验证的请求
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 允许 gemini_routes 和 openai_routes 中的端点绕过身份验证
    if (request.url.path not in ["/", "/auth"] and 
        not request.url.path.startswith("/static") and
        not request.url.path.startswith("/gemini") and
        not request.url.path.startswith("/v1") and
        not request.url.path.startswith("/v1beta") and
        not request.url.path.startswith("/health") and
        not request.url.path.startswith("/hf")):
        auth_token = request.cookies.get("auth_token")
        if not auth_token or not verify_auth_token(auth_token):
            logger.warning(f"Unauthorized access attempt to {request.url.path}")
            return RedirectResponse(url="/")
        logger.debug("Request authenticated successfully")
    response = await call_next(request)
    return response

# 添加请求日志中间件
# app.add_middleware(RequestLoggingMiddleware)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体的域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 明确指定允许的HTTP方法
    allow_headers=["*"],  # 生产环境建议配置具体的请求头
    expose_headers=["*"],  # 允许前端访问的响应头
    max_age=600,  # 预检请求缓存时间(秒)
)

# 包含所有路由
app.include_router(openai_routes.router, prefix="/v1", tags=["OpenAI"])
app.include_router(gemini_routes.router, prefix="/v1", tags=["Gemini"])
app.include_router(claude_routes.router, prefix="/v1", tags=["Claude"])
app.include_router(gemini_routes.router_v1beta)


@app.get("/", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


@app.post("/auth")
async def authenticate(request: Request):
    try:
        form = await request.form()
        auth_token = form.get("auth_token")
        if not auth_token:
            logger.warning("Authentication attempt with empty token")
            return RedirectResponse(url="/", status_code=302)
        
        if verify_auth_token(auth_token):
            logger.info("Successful authentication")
            response = RedirectResponse(url="/keys", status_code=302)
            response.set_cookie(key="auth_token", value=auth_token, httponly=True, max_age=3600)
            return response
        logger.warning("Failed authentication attempt with invalid token")
        return RedirectResponse(url="/", status_code=302)
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return RedirectResponse(url="/", status_code=302)

@app.get("/keys", response_class=HTMLResponse)
async def keys_page(request: Request):
    try:
        auth_token = request.cookies.get("auth_token")
        if not auth_token or not verify_auth_token(auth_token):
            logger.warning("Unauthorized access attempt to keys page")
            return RedirectResponse(url="/", status_code=302)
        
        keys_status = await key_manager.get_keys_by_status()
        total = len(keys_status["valid_keys"]) + len(keys_status["invalid_keys"])
        logger.info(f"Keys status retrieved successfully. Total keys: {total}")
        return templates.TemplateResponse("keys_status.html", {
            "request": request,
            "valid_keys": keys_status["valid_keys"],
            "invalid_keys": keys_status["invalid_keys"],
            "total": total
        })
    except Exception as e:
        logger.error(f"Error retrieving keys status: {str(e)}")
        raise


@app.get("/health")
async def health_check(request: Request):
    logger.info("Health check endpoint called")
    return {"status": "healthy"}
    
    
if __name__ == "__main__":
    logger.info("Starting application server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
