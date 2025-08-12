from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
import traceback
import time
from PyPDF2 import PdfMerger

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Debug Melhorado</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .debug { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2196f3; }
        textarea { width: 100%; height: 200px; padding: 10px; font-family: monospace; }
        button { width: 100%; padding: 15px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { display: none; text-align: center; margin-top: 20px; }
        .spinner { border: 2px solid #f3f3f3; border-top: 2px solid #007bff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .debug-log { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Debug Melhorado - Identificar Erro Indefinido</p>
    </div>
    
    <div class="debug">
        <h3>🔍 Debug Ativo:</h3>
        <ul>
            <li>📊 Logs detalhados no console</li>
            <li>⏱️ Timeout de 10 minutos para códigos grandes</li>
            <li>🔧 Tratamento robusto de erros</li>
            <li>📝 Log de cada etapa do processamento</li>
        </ul>
    </div>
    
    <form id="zplForm">
        <label for="zplCode">Cole seu código ZPL:</label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Debug ativo - logs detalhados!"></textarea><br><br>
        <button type="submit">🔍 Gerar PDF (Debug Ativo)</button>
    </form>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p id="loadingText">Processando com debug...</p>
        <p><small>Timeout: 10 minutos</small></p>
    </div>
    
    <div id="result"></div>
    
    <div class="debug-log" id="debugLog" style="display: none;">
        <h4>📝 Log de Debug:</h4>
        <div id="logContent"></div>
    </div>
    
    <script>
        function addLog(message) {
            const logContent = document.getElementById('logContent');
            const debugLog = document.getElementById('debugLog');
            const timestamp = new Date().toLocaleTimeString();
            logContent.innerHTML += `[${timestamp}] ${message}<br>`;
            debugLog.style.display = 'block';
            logContent.scrollTop = logContent.scrollHeight;
            console.log(`[ZPL Debug] ${message}`);
        }
        
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            addLog('🚀 Iniciando processamento...');
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                addLog('❌ Código ZPL vazio');
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            addLog(`📊 Código ZPL: ${zplCode.length} caracteres`);
            
            const button = e.target.querySelector('button');
            const result = document.getElementById('result');
            const loading = document.getElementById('loading');
            
            button.disabled = true;
            button.textContent = '⏳ Processando com Debug...';
            loading.style.display = 'block';
            result.innerHTML = '';
            
            addLog('📡 Enviando requisição para servidor...');
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => {
                    controller.abort();
                    addLog('⏰ Timeout de 10 minutos atingido');
                }, 10 * 60 * 1000); // 10 minutos
                
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode }),
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                addLog(`📨 Resposta recebida: Status ${response.status}`);
                
                if (response.ok) {
                    addLog('✅ Resposta OK - Baixando PDF...');
                    const blob = await response.blob();
                    addLog(`📄 PDF recebido: ${blob.size} bytes`);
                    
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'etiquetas_debug.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    result.innerHTML = '<div class="result success">✅ PDF gerado com sucesso!</div>';
                    addLog('🎉 Download concluído com sucesso!');
                } else {
                    addLog(`❌ Erro HTTP: ${response.status}`);
                    
                    const contentType = response.headers.get('content-type');
                    addLog(`📋 Content-Type: ${contentType}`);
                    
                    if (contentType && contentType.includes('application/json')) {
                        const error = await response.json();
                        addLog(`📝 Erro JSON: ${JSON.stringify(error)}`);
                        result.innerHTML = `<div class="result error">❌ ${error.error || 'Erro desconhecido'}</div>`;
                    } else {
                        const errorText = await response.text();
                        addLog(`📝 Erro Texto: ${errorText.substring(0, 200)}...`);
                        result.innerHTML = `<div class="result error">❌ Erro do servidor: ${response.status}</div>`;
                    }
                }
            } catch (error) {
                addLog(`💥 Erro JavaScript: ${error.name} - ${error.message}`);
                
                if (error.name === 'AbortError') {
                    result.innerHTML = '<div class="result error">❌ Timeout: Processamento cancelado após 10 minutos</div>';
                } else {
                    result.innerHTML = `<div class="result error">❌ Erro de conexão: ${error.message}</div>`;
                }
            } finally {
                button.disabled = false;
                button.textContent = '🔍 Gerar PDF (Debug Ativo)';
                loading.style.display = 'none';
                addLog('🏁 Processamento finalizado');
            }
        });
    </script>
</body>
</html>'''

@app.errorhandler(413)
def request_entity_too_large(error):
    print("❌ Erro 413: Request Entity Too Large")
    return jsonify({'error': 'Arquivo muito grande. Limite: 100MB'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    print(f"❌ Erro 500: {str(error)}")
    return jsonify({'error': f'Erro interno do servidor: {str(error)}'}), 500

@app.route('/generate', methods=['POST'])
def generate():
    start_time = time.time()
    
    try:
        print("🚀 === INÍCIO DO PROCESSAMENTO ===")
        
        # Verificar se é JSON
        if not request.is_json:
            print("❌ Requisição não é JSON")
            return jsonify({'error': 'Requisição deve ser JSON'}), 400
        
        data = request.get_json()
        print(f"📊 Dados recebidos: {type(data)}")
        
        if not data:
            print("❌ Dados JSON vazios")
            return jsonify({'error': 'Dados JSON vazios'}), 400
        
        zpl_code = data.get('zpl', '').strip()
        print(f"📝 Código ZPL: {len(zpl_code)} caracteres")
        
        if not zpl_code:
            print("❌ Código ZPL vazio")
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        
        # Detectar blocos ZPL
        print("🔍 Detectando blocos ZPL...")
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        print(f"📦 Blocos detectados: {len(zpl_blocks)}")
        
        if not zpl_blocks:
            print("⚠️ Nenhum bloco detectado, tratando como código único")
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            zpl_blocks = [zpl_code]
            print(f"📦 Bloco único criado: {len(zpl_blocks[0])} caracteres")
        
        # Processar blocos
        print("🔄 Iniciando processamento...")
        result = process_blocks_debug(zpl_blocks)
        
        elapsed = time.time() - start_time
        print(f"✅ Processamento concluído em {elapsed:.1f} segundos")
        
        return result
        
    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        print(f"💥 ERRO CRÍTICO após {elapsed:.1f}s:")
        print(f"📝 Mensagem: {error_msg}")
        print(f"🔍 Traceback: {traceback_str}")
        
        return jsonify({
            'error': f'Erro interno: {error_msg}',
            'traceback': traceback_str,
            'elapsed': elapsed
        }), 500

def process_blocks_debug(zpl_blocks):
    """Processa blocos com debug detalhado"""
    try:
        print(f"📊 Processando {len(zpl_blocks)} blocos")
        
        # Para teste, processar apenas os primeiros 3 blocos
        test_blocks = zpl_blocks[:3]
        print(f"🧪 TESTE: Processando apenas {len(test_blocks)} blocos para debug")
        
        batch_zpl = '\n'.join(test_blocks)
        print(f"📝 ZPL do lote: {len(batch_zpl)} caracteres")
        
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/pdf'
        }
        
        print("📡 Enviando para Labelary...")
        response = requests.post(url, data=batch_zpl, headers=headers, timeout=60)
        print(f"📨 Resposta Labelary: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ PDF recebido: {len(response.content)} bytes")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            print(f"💾 Arquivo temporário: {temp_file.name}")
            
            return send_file(temp_file.name, as_attachment=True, download_name='etiquetas_debug.pdf')
        else:
            error_msg = f"Erro Labelary: {response.status_code}"
            if response.text:
                error_msg += f" - {response.text[:200]}"
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'error': f'Erro no processamento: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor debug...")
    app.run(host='0.0.0.0', port=5000, debug=True)
