from flask import Flask, request, render_template_string, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS
import os
import tempfile
import requests
import io
import base64
from PyPDF2 import PdfMerger
import uuid
import time

app = Flask(__name__)
app.secret_key = 'zpl-generator-manus-2025'
CORS(app)

# Template HTML de Login Manus
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Login Manus</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 400px;
            width: 90%;
            text-align: center;
        }
        .logo { font-size: 48px; margin-bottom: 10px; }
        .title { font-size: 28px; color: #333; margin-bottom: 10px; font-weight: 600; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 16px; }
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 500; }
        input[type="email"], input[type="password"] {
            width: 100%; padding: 15px; border: 2px solid #e1e5e9;
            border-radius: 10px; font-size: 16px; transition: border-color 0.3s;
        }
        input[type="email"]:focus, input[type="password"]:focus {
            outline: none; border-color: #667eea;
        }
        .login-btn {
            width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 15px; border: none; border-radius: 10px;
            font-size: 18px; font-weight: 600; cursor: pointer; transition: transform 0.2s;
        }
        .login-btn:hover { transform: translateY(-2px); }
        .footer { margin-top: 30px; color: #666; font-size: 14px; }
        .manus-link { color: #667eea; text-decoration: none; font-weight: 500; }
        .error { background: #fee; color: #c33; padding: 10px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #fcc; }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🏷️</div>
        <h1 class="title">ZPL Generator</h1>
        <p class="subtitle">Acesso via Manus AI</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="email">Email Manus:</label>
                <input type="email" id="email" name="email" required placeholder="seu@email.com">
            </div>
            <div class="form-group">
                <label for="password">Senha:</label>
                <input type="password" id="password" name="password" required placeholder="Sua senha">
            </div>
            <button type="submit" class="login-btn">🚀 Entrar no ZPL Generator</button>
        </form>
        <div class="footer">
            <p>Desenvolvido com <a href="https://manus.ai" class="manus-link">Manus AI</a></p>
            <p>🌟 Tecnologia de ponta para geração de etiquetas</p>
        </div>
    </div>
</body>
</html>
'''

# Template HTML Principal
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Gerador Profissional</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #f8f9fa; line-height: 1.6;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-content {
            max-width: 1200px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .logo-section { display: flex; align-items: center; gap: 15px; }
        .logo { font-size: 36px; }
        .title-section h1 { font-size: 28px; font-weight: 600; }
        .title-section p { opacity: 0.9; font-size: 16px; }
        .user-section { text-align: right; }
        .logout-btn {
            background: rgba(255,255,255,0.2); color: white; padding: 8px 16px;
            border: 1px solid rgba(255,255,255,0.3); border-radius: 20px;
            text-decoration: none; font-size: 14px; transition: background 0.3s;
        }
        .logout-btn:hover { background: rgba(255,255,255,0.3); }
        .container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
        .main-card {
            background: white; border-radius: 15px; padding: 30px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1); margin-bottom: 30px;
        }
        .form-group { margin-bottom: 25px; }
        label { display: block; margin-bottom: 10px; font-weight: 600; color: #333; font-size: 16px; }
        textarea {
            width: 100%; padding: 15px; border: 2px solid #e1e5e9; border-radius: 10px;
            font-family: 'Courier New', monospace; font-size: 14px; resize: vertical;
            min-height: 200px; transition: border-color 0.3s;
        }
        textarea:focus { outline: none; border-color: #667eea; }
        .generate-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 15px 30px; border: none; border-radius: 10px;
            font-size: 18px; font-weight: 600; cursor: pointer; transition: transform 0.2s;
            display: inline-flex; align-items: center; gap: 10px;
        }
        .generate-btn:hover { transform: translateY(-2px); }
        .generate-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .result-card {
            background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 15px;
            padding: 25px; margin-top: 25px; display: none;
        }
        .result-card.success { background: #d4edda; border-color: #c3e6cb; }
        .result-card.error { background: #f8d7da; border-color: #f5c6cb; }
        .download-btn {
            background: #28a745; color: white; padding: 12px 25px; border: none;
            border-radius: 8px; text-decoration: none; display: inline-flex;
            align-items: center; gap: 8px; font-weight: 500; transition: background 0.3s;
        }
        .download-btn:hover { background: #218838; }
        .info-section {
            background: #e3f2fd; border-left: 4px solid #2196f3; padding: 20px;
            border-radius: 0 10px 10px 0; margin-bottom: 25px;
        }
        .info-section h3 { color: #1976d2; margin-bottom: 10px; }
        .info-section p { color: #424242; margin-bottom: 8px; }
        .footer {
            text-align: center; padding: 30px 20px; color: #666;
            border-top: 1px solid #e1e5e9; margin-top: 50px;
        }
        .loading { display: none; text-align: center; padding: 20px; }
        .spinner {
            border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%;
            width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">🏷️</div>
                <div class="title-section">
                    <h1>ZPL Generator Pro</h1>
                    <p>Gerador Profissional de Etiquetas ZPL</p>
                </div>
            </div>
            <div class="user-section">
                <p>👤 {{ user_email }}</p>
                <a href="/logout" class="logout-btn">🚪 Sair</a>
            </div>
        </div>
    </header>
    <div class="container">
        <div class="info-section">
            <h3>📋 Como usar:</h3>
            <p>• Cole seu código ZPL no campo abaixo</p>
            <p>• Clique em "Gerar PDF" para processar</p>
            <p>• O sistema processa até 50 etiquetas por vez</p>
            <p>• Tamanho otimizado: 8 x 2,5 cm (impressoras Argox)</p>
        </div>
        <div class="main-card">
            <form id="zplForm">
                <div class="form-group">
                    <label for="zplCode">📝 Cole seu código ZPL aqui:</label>
                    <textarea id="zplCode" name="zplCode" placeholder="^XA^FO50,50^A0N,50,50^FDSua Etiqueta^FS^XZ" required></textarea>
                </div>
                <button type="submit" class="generate-btn" id="generateBtn">🚀 Gerar PDF</button>
            </form>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Processando etiquetas via Labelary.com...</p>
                <p><small>Aguarde, pode levar alguns segundos</small></p>
            </div>
            <div id="result" class="result-card">
                <h3 id="resultTitle">✅ PDF Gerado com Sucesso!</h3>
                <p id="resultMessage">Seu arquivo PDF foi gerado e está pronto para download.</p>
                <div id="downloadSection" style="margin-top: 15px;">
                    <a id="downloadLink" href="#" class="download-btn">📥 Baixar PDF</a>
                </div>
            </div>
        </div>
    </div>
    <footer class="footer">
        <p>💡 Desenvolvido com <strong>Manus AI</strong></p>
        <p>🚀 Hospedado com Railway - Disponível 24/7</p>
        <p>🔧 Processamento via Labelary.com para máxima qualidade</p>
    </footer>
    <script>
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) { alert('Por favor, insira o código ZPL'); return; }
            document.getElementById('generateBtn').disabled = true;
            document.getElementById('generateBtn').innerHTML = '⏳ Processando...';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';
            try {
                const response = await fetch('/generate-pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl_code: zplCode })
                });
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    document.getElementById('downloadLink').href = url;
                    document.getElementById('downloadLink').download = 'etiquetas_zpl.pdf';
                    document.getElementById('result').className = 'result-card success';
                    document.getElementById('result').style.display = 'block';
                } else {
                    const error = await response.json();
                    document.getElementById('resultTitle').textContent = '❌ Erro ao Gerar PDF';
                    document.getElementById('resultMessage').textContent = error.error || 'Erro desconhecido';
                    document.getElementById('downloadSection').style.display = 'none';
                    document.getElementById('result').className = 'result-card error';
                    document.getElementById('result').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('resultTitle').textContent = '❌ Erro de Conexão';
                document.getElementById('resultMessage').textContent = 'Erro: ' + error.message;
                document.getElementById('downloadSection').style.display = 'none';
                document.getElementById('result').className = 'result-card error';
                document.getElementById('result').style.display = 'block';
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('generateBtn').disabled = false;
                document.getElementById('generateBtn').innerHTML = '🚀 Gerar PDF';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template_string(MAIN_TEMPLATE, user_email=session['user_email'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if email and password and '@' in email:
            session['user_email'] = email
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Email ou senha inválidos")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    if 'user_email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        data = request.get_json()
        zpl_code = data.get('zpl_code', '').strip()
        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        zpl_commands = [cmd.strip() for cmd in zpl_code.split('^XZ') if cmd.strip()]
        if not zpl_commands:
            return jsonify({'error': 'Código ZPL inválido'}), 400
        pdf_merger = PdfMerger()
        batch_size = 50
        for i in range(0, len(zpl_commands), batch_size):
            batch = zpl_commands[i:i+batch_size]
            batch_zpl = ''
            for cmd in batch:
                if cmd:
                    batch_zpl += cmd + '^XZ\n'
            pdf_data = generate_pdf_via_labelary(batch_zpl)
            if pdf_data:
                pdf_merger.append(io.BytesIO(pdf_data))
        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        pdf_merger.close()
        output_buffer.seek(0)
        return send_file(
            output_buffer,
            as_attachment=True,
            download_name=f'etiquetas_zpl_{int(time.time())}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

def generate_pdf_via_labelary(zpl_code):
    try:
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/pdf'
        }
        response = requests.post(url, data=zpl_code, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Erro Labelary: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao conectar com Labelary: {str(e)}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
