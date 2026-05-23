// 静态侧边栏列表（纯展示，无点击功能）
    const sampleConversations = [
        { title: "资讯"},
        { title: "战绩"},
        { title: "...(代表其他)"},
    ];

    function renderSidebar() {
        const container = document.getElementById('conversationList');
        if (!container) return;
        container.innerHTML = '';
        sampleConversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = 'conversation-item';
            item.innerHTML = `
                <!--这里可以换成想要的图片-->
                <a href="#" class="conv-title">${escapeHtml(conv.title)}</a>
                
            `;
            container.appendChild(item);
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }

    // 移动端侧边栏控制
    function openSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('overlay');
        sidebar.classList.add('open');
        if (overlay) {
            overlay.style.visibility = 'visible';
            overlay.style.opacity = '1';
        }
    }
    function closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('overlay');
        sidebar.classList.remove('open');
        if (overlay) {
            overlay.style.visibility = 'hidden';
            overlay.style.opacity = '0';
        }
    }

    // 初始化侧边栏内容
    renderSidebar();

    // 绑定导航栏上的汉堡按钮和遮罩
    const toggleBtn = document.getElementById('navbarToggleBtn');
    const overlay = document.getElementById('overlay');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', openSidebar);
    }
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // 窗口resize时关闭移动端侧边栏（如果变宽）
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            closeSidebar();
        }
    });


        // 标签切换逻辑
        function switchTab(type) {
            // 重置所有标签
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            // 隐藏所有内容
            document.querySelectorAll('.content-block').forEach(block => {
                block.classList.remove('show');
            });

            // 激活对应标签&内容
            if(type === 'mine'){
                document.getElementById('tabMine').classList.add('active');
                document.getElementById('contentMine').classList.add('show');
            }else if(type === 'recommend'){
                document.getElementById('tabRecommend').classList.add('active');
                document.getElementById('contentRecommend').classList.add('show');
            }else if(type === 'special'){
                document.getElementById('tabSpecial').classList.add('active');
                document.getElementById('contentSpecial').classList.add('show');
            }
        }


