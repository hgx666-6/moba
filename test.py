from playwright.sync_api import sync_playwright
import time
import pyperclip
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import pymysql
import threading
from queue import Queue
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = "abcdef123456"

# 头像上传配置
UPLOAD_FOLDER = os.path.join('static', 'avatar')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ======================
# 数据库配置
# ======================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "moba",
    "charset": "utf8mb4"
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# ======================
# AI 线程安全队列
# ======================
task_queue = Queue()
result_queue = Queue()
ai_ready = False

# ======================
# AI 后台线程
# ======================
def ai_worker():
    global ai_ready
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-notifications",
                "--no-first-run",
                "--disable-infobars",
                "--start-maximized",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(viewport={"width": 1536, "height": 960})
        page = context.new_page()
        page.goto("https://chat.deepseek.com/")
        time.sleep(1)

        try:
            w = page.viewport_size["width"]
            h = page.viewport_size["height"]
            x1 = int(w * 0.36)
            x2 = int(w * 0.42)
            y1 = int(h * 0.60)
            y2 = int(h * 0.72)
            click_x = x1 + (x2 - x1) // 2
            click_y = y1 + (y2 - y1) // 2
            page.mouse.click(click_x, click_y)
        except:
            pass

        try:
            time.sleep(1)
            page.locator("input[type='text']").fill("19863011699")
            page.locator("input[type='password']").fill("heguangxiao0425.")
            page.locator("button:has-text('登录')").click()
            time.sleep(3)
        except:
            pass

        print("✅ AI 登录成功，等待提问...")
        ai_ready = True

        while True:
            if not task_queue.empty():
                question = task_queue.get()
                try:
                    pyperclip.copy("")
                    time.sleep(0.2)
                    suffix = "，回答在300到400字之间"
                    question = (question + suffix)[:200]

                    page.locator("textarea").first.fill(question)
                    time.sleep(0.3)
                    page.locator("div[role='button']:has(svg path[d*='M8.3125'])").first.click()
                    print(f"🗣️ 已提问: {question}")
                    page.keyboard.press("End")

                    print("⏳ 等待AI回答完成...")
                    time.sleep(15)
                    toolbar = page.locator("div[class*='_965abe9']").last
                    toolbar.wait_for(state="visible", timeout=120000)

                    copy_btn = toolbar.locator("div[role='button']").first
                    copy_btn.click()
                    time.sleep(0.5)

                    answer = pyperclip.paste().strip()
                    result_queue.put(answer)
                    print("✅ 复制成功！")

                except Exception as e:
                    result_queue.put(f"AI出错：{str(e)}")
                    print("错误：", e)
            time.sleep(0.1)

# ======================
# 启动AI
# ======================
def start_ai():
    t = threading.Thread(target=ai_worker, daemon=True)
    t.start()

# ======================
# 【权限装饰器 严格分离】
# 1. 运营商专属权限装饰器
# ======================
def operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get("login_user")
        if not username:
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT role FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()
        if not user or user['role'] != '运营商':
            return "<script>alert('无运营商管理权限！');history.back()</script>"
        return f(*args, **kwargs)
    return decorated_function

# ======================
# 2. 管理员专属权限装饰器
# ======================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get("login_user")
        if not username:
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT role FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()
        if not user or user['role'] != '管理员':
            return "<script>alert('无管理员管理权限！');history.back()</script>"
        return f(*args, **kwargs)
    return decorated_function

# ======================
# 路由
# ======================
@app.route('/login')
def login():
    if not ai_ready:
        start_ai()
    return render_template('register.html')

# 【登录接口 角色自动分流跳转】
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
                                                                                                                              

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role=%s", (username, password, role))
    user = cursor.fetchone()

    # ======================
    # 【调试日志：数据库查到的结果】
    # ======================
   

    conn.close()

    if user:
        session['login_user'] = username
        if role == "运营商":
            return jsonify({"success": True, "msg": "登录成功", "jump": "/operator"})
        elif role == "管理员":
            return jsonify({"success": True, "msg": "登录成功", "jump": "/admin"})
        else:
            return jsonify({"success": True, "msg": "登录成功", "jump": "/home"})
    
    
    return jsonify({"success": False, "msg": "账号密码错误"})

@app.route('/home')
def home():
    username = session.get("login_user", "未知用户")
    user = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        conn.close()
    except:
        pass
    return render_template('主页.html', login_user=username, user=user)

@app.route('/zhanji')
def zhanji():
    username = session.get("login_user", "未知用户")
    user = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            user_id = user['id']
            cursor.execute("SELECT * FROM record WHERE `user id` = %s", (user_id,))
        else:
            cursor.execute("SELECT * FROM record WHERE 1=2")
        
        record_list = cursor.fetchall()
        total_game = len(record_list)

        win_count = 0
        lose_count = 0
        for r in record_list:
            if r['result'] == '胜利':
                win_count += 1
            else:
                lose_count += 1
        win_rate = 0
        if total_game > 0:
            win_rate = round((win_count / total_game) * 100, 1)

        sum_k = sum_d = sum_a = 0
        sum_money = 0
        sum_damage_per = 0
        sum_dtp = 0
        sum_participation = 0

        for row in record_list:
            kda_str = row['kda']
            k_list = kda_str.split('/')
            k = int(k_list[0])
            d = int(k_list[1])
            a = int(k_list[2])
            sum_k += k
            sum_d += d
            sum_a += a

            money_str = str(row['money']).replace('k','').replace('K','')
            sum_money += float(money_str)

            damage_p = float(str(row['damage percentage']).replace('%',''))
            sum_damage_per += damage_p

            dtp_p = float(str(row['dtp']).replace('%',''))
            sum_dtp += dtp_p

            part_p = float(str(row['participation rate']).replace('%',''))
            sum_participation += part_p

        avg_k = round(sum_k / total_game, 1) if total_game>0 else 0
        avg_d = round(sum_d / total_game, 1) if total_game>0 else 0
        avg_a = round(sum_a / total_game, 1) if total_game>0 else 0
        avg_kda_ratio = round((avg_k + avg_a) / avg_d, 1) if avg_d != 0 else 0

        avg_money = round(sum_money / total_game, 1) if total_game>0 else 0
        avg_damage = round(sum_damage_per / total_game, 1) if total_game>0 else 0
        avg_dtp = round(sum_dtp / total_game, 1) if total_game>0 else 0
        avg_part = round(sum_participation / total_game, 1) if total_game>0 else 0

        conn.close()
    except Exception as e:
        print("数据库查询错误",e)
        record_list = []
        total_game = 0
        win_count=0;lose_count=0;win_rate=0
        avg_k=0;avg_d=0;avg_a=0;avg_kda_ratio=0
        avg_money=0;avg_damage=0;avg_dtp=0;avg_part=0

    return render_template('战绩.html',
        login_user=username,
        user=user,
        record_list=record_list,
        total_game=total_game,
        win_count=win_count,
        lose_count=lose_count,
        win_rate=win_rate,
        avg_kda_ratio=avg_kda_ratio,
        avg_k=avg_k,avg_d=avg_d,avg_a=avg_a,
        avg_part=avg_part,
        avg_money=avg_money,
        avg_damage=avg_damage,
        avg_dtp=avg_dtp
    )

@app.route('/tiezi')
def tiezi():
    username = session.get("login_user")
    if not username:
        return redirect(url_for('login'))

    cate = request.args.get('cate', 'all')

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT whichgame FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return redirect(url_for('login'))

    user_game = user['whichgame']

    # 用户端统一排序 id ASC 小ID置顶，仅展示status=1合规帖子
    if cate == 'all':
        sql = """
            SELECT id, title, content, category, whichgame, views
            FROM posts 
            WHERE status=1 AND whichgame=%s
            ORDER BY id ASC
        """
        cursor.execute(sql, (user_game,))
    else:
        sql = """
            SELECT id, title, content, category, whichgame, views
            FROM posts 
            WHERE status=1 AND whichgame=%s AND category=%s
            ORDER BY id ASC
        """
        cursor.execute(sql, (user_game, cate))

    posts = cursor.fetchall()
    conn.close()

    return render_template('帖子.html', posts=posts, login_user=username, cate=cate)

@app.route('/post/detail/<int:post_id>')
def post_detail(post_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
        SELECT p.*, u.username as author_name, u.avatar as author_avatar
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        WHERE p.id=%s
    """, (post_id,))
    post = cursor.fetchone()
    
    if not post:
        conn.close()
        return "<script>alert('帖子不存在');history.back()</script>"

    cursor.execute("UPDATE posts SET views = views + 1 WHERE id=%s", (post_id,))
    conn.commit()
    
    cursor.execute("""
        SELECT e.*, u.username, u.avatar
        FROM evaluation e
        LEFT JOIN users u ON e.`user id` = u.id
        WHERE e.`post id` = %s
        ORDER BY e.id ASC
    """, (post_id,))
    comments = cursor.fetchall()
    
    conn.close()
    return render_template('帖子详情.html', post=post, comments=comments)

@app.route('/post/comment/<int:post_id>', methods=['POST'])
def post_comment(post_id):
    username = session.get("login_user")
    if not username:
        return redirect(url_for('login'))

    content = request.form.get("content", "").strip()
    if not content:
        return redirect(f"/post/detail/{post_id}")

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return redirect(f"/post/detail/{post_id}")

    user_id = user['id']

    cursor.execute("""
        INSERT INTO evaluation (`user id`, `post id`, content)
        VALUES (%s, %s, %s)
    """, (user_id, post_id, content))
    conn.commit()
    conn.close()

    return redirect(f"/post/detail/{post_id}")

@app.route('/chuzhuang')
def chuzhuang():
    username = session.get("login_user", "未知用户")
    total_game = 0
    win_rate = 0
    user = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        
        if user:
            user_id = user['id']
            cursor.execute("SELECT result FROM record WHERE `user id`=%s", (user_id,))
            records = cursor.fetchall()
            total_game = len(records)
            win_count = sum(1 for r in records if r['result'] == '胜利')
            if total_game > 0:
                win_rate = round((win_count / total_game) * 100, 1)
        conn.close()
    except Exception as e:
        print("出装页错误", e)

    return render_template('出装.html',
        login_user=username,
        user=user,
        win_rate=win_rate,
        total_game=total_game
    )

@app.route('/')
def index():
    return "<h1>MOBA 系统</h1><a href='/login'>前往登录</a>"

# ======================
# 用户通用接口
# ======================
@app.route('/api/update-password', methods=['POST'])
def update_password():
    data = request.get_json()
    username = session.get("login_user")
    if not username:
        return jsonify({"success": False, "msg": "请登录"})
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, data.get('oldPassword')))
    if not cursor.fetchone():
        return jsonify({"success": False, "msg": "原密码错误"})
    cursor.execute("UPDATE users SET password=%s WHERE username=%s", (data.get('newPassword'), username))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "msg": "修改成功"})

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    data = request.get_json()
    username = session.get("login_user")
    if not username:
        return jsonify({"success": False, "msg": "请登录"})
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""UPDATE users SET sex=%s, birth=%s, introduction=%s, email=%s, phone=%s, area=%s WHERE username=%s""",
        (data.get('sex'), data.get('birth'), data.get('introduction'), data.get('email'), data.get('phone'), data.get('area'), username))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "msg": "保存成功"})

# 头像Base64上传接口
@app.route('/api/update-avatar', methods=['POST'])
def update_avatar():
    try:
        username = session.get("login_user")
        if not username:
            return jsonify({"success": False, "msg": "请登录"})
        data = request.get_json()
        avatar_base64 = data.get('avatarBase64', '')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET avatar=%s WHERE username=%s", (avatar_base64, username))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "msg": "头像修改成功！"})
    except Exception as e:
        return jsonify({"success":False,"msg":"上传失败："+str(e)})

# AI问答接口
@app.route('/api/ask-ai', methods=['POST'])
def api_ask_ai():
    if not ai_ready:
        return jsonify({"answer": "AI 启动中，请稍候..."})
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"answer": "请输入问题"})
    task_queue.put(question)
    ans = result_queue.get()
    return jsonify({"answer": ans})

# 战绩查询接口
@app.route("/getRecord")
def getRecord():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify([])
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM record WHERE `user id` = %s", (user_id,))
        data = cursor.fetchall()
        conn.close()
        return jsonify(data)
    except:
        return jsonify([])

# 用户发帖接口
@app.route('/post/add', methods=['GET', 'POST'])
def add_post():
    username = session.get("login_user")
    if not username:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, whichgame FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if request.method == "GET":
        conn.close()
        return render_template("发帖.html", login_user=username)
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    category = request.form.get("category", "").strip()
    if not title or not content or not category:
        conn.close()
        return "<script>alert('标题、内容、分类都不能为空');history.back()</script>"
    user_id = user["id"]
    whichgame = user["whichgame"]
    cursor.execute("""
        INSERT INTO posts (title, content, user_id, whichgame, category, status, views)
        VALUES (%s, %s, %s, %s, %s, 1, 0)
    """, (title, content, user_id, whichgame, category))
    conn.commit()
    conn.close()
    return redirect(url_for('tiezi'))

# 游戏攻略接口
@app.route('/guide')
def guide():
    username = session.get("login_user")
    if not username:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT whichgame FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return redirect(url_for('login'))
    user_game = user['whichgame']
    cursor.execute("""
        SELECT id, title, content, whichgame 
        FROM news 
        WHERE whichgame=%s
        ORDER BY id DESC
    """, (user_game,))
    news_list = cursor.fetchall()
    conn.close()
    return render_template('攻略.html', news=news_list, login_user=username)

@app.route('/guide/detail/<int:news_id>')
def guide_detail(news_id):
    username = session.get("login_user")
    if not username:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM news WHERE id=%s", (news_id,))
    news = cursor.fetchone()
    conn.close()
    if not news:
        return "<script>alert('攻略不存在');history.back()</script>"
    return render_template('攻略详情.html', news=news, login_user=username)

# ======================================================
# 【运营商后台 /operator 专属路由&接口】
# 权限：查看全部帖子、改分类、置顶（同游戏ID互换）
# 无权限：修改status合规状态
# ======================================================
@app.route('/operator')
@operator_required
def operator():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT p.*, u.username as author
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)
    all_posts = cursor.fetchall()
    conn.close()
    return render_template('operator.html', posts=all_posts)

# 运营商专属：修改帖子分类接口
@app.route('/api/operator/edit-category', methods=['POST'])
@operator_required
def edit_post_category():
    data = request.get_json()
    post_id = data.get("post_id")
    new_category = data.get("category")
    if not post_id or not new_category:
        return jsonify({"success":False,"msg":"参数不全"})
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET category=%s WHERE id=%s", (new_category, post_id))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"msg":"分类修改成功"})

# 运营商专属：帖子置顶（同游戏ID互换）
@app.route('/api/operator/recommend', methods=['POST'])
@operator_required
def post_recommend():
    data = request.get_json()
    post_id = data.get("post_id")
    if not post_id:
        return jsonify({"success":False,"msg":"帖子ID错误"})
    conn = get_db_connection()
    cursor = conn.cursor()
    # 先获取该帖子所属游戏
    cursor.execute("SELECT whichgame FROM posts WHERE id=%s", (post_id,))
    post_info = cursor.fetchone()
    if not post_info:
        conn.close()
        return jsonify({"success":False,"msg":"帖子不存在"})
    whichgame = post_info[0]
    # 查询该游戏下最小ID
    cursor.execute("SELECT MIN(id) FROM posts WHERE whichgame=%s", (whichgame,))
    min_id = cursor.fetchone()[0]
    if min_id == post_id:
        conn.close()
        return jsonify({"success":False,"msg":"已是同游戏置顶，无需操作"})
    # 安全三步ID互换（临时ID避免主键冲突）
    temp_id = 9999999
    cursor.execute("UPDATE posts SET id=%s WHERE id=%s", (temp_id, post_id))
    cursor.execute("UPDATE posts SET id=%s WHERE id=%s", (post_id, min_id))
    cursor.execute("UPDATE posts SET id=%s WHERE id=%s", (min_id, temp_id))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"msg":"帖子置顶成功（同游戏ID互换）"})

# ======================================================
# 【管理员后台 /admin 专属路由&接口】
# 权限：查看全部帖子全量信息、**仅修改status合规状态**
# 无权限：修改分类、无置顶推荐功能
# ======================================================
@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # 管理员查看所有帖子全部字段（含status）
    cursor.execute("""
        SELECT p.*, u.username as author
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        ORDER BY p.id DESC
    """)
    all_posts = cursor.fetchall()
    conn.close()
    return render_template('admin.html', posts=all_posts)

# 管理员专属：仅修改帖子status状态接口
@app.route('/api/admin/edit-status', methods=['POST'])
@admin_required
def admin_edit_status():
    data = request.get_json()
    post_id = data.get("post_id")
    status = data.get("status")
    if not post_id or status is None:
        return jsonify({"success":False,"msg":"参数不全"})
    # status严格限制 1合规 / 0违规
    if status not in ["0","1"]:
        return jsonify({"success":False,"msg":"状态值非法"})
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET status=%s WHERE id=%s", (status, post_id))
    conn.commit()
    conn.close()
    return jsonify({"success":True,"msg":"帖子状态修改成功！1=合规展示，0=违规隐藏"})

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)