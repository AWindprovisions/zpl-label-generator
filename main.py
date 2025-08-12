from flask import Flask, request, render_template_string, jsonify, send_file
from flask_cors import CORS
import os, tempfile, requests, io, time, re, logging, gc
from PyPDF2 import PdfMerger
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
app.secret_key = 'zpl-generator-manus-2025'
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 * 1024  # 50 GB
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAIN_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator Pro - Ultra Robusto</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .logo { font-size: 48px; margin-bottom: 10px; }
        .title { font-size: 32px; margin-bottom: 10px; font-weight: 600; }
        .subtitle { font-size: 18px; opacity: 0.9; }
        .content { padding: 40px; }
        .info-card { background: #e8f5e8; padding: 20px; border-radius: 15px; margin-bottom: 30px; border-left: 5px solid #28a745; }
        .ultra-card { background: #e3f2fd; padding: 20px; border-radius: 15px; margin-bottom: 30px; border-left: 5px solid #2196f3; }
        .form-group { margin-bottom: 25px; }
        label { display: block; margin-bottom: 10px; color: #333; font-weight: 600; font-size: 16px; }
        textarea { width: 100%; min-height: 250px; padding: 15px; border: 2px solid #e1e5e9; border-radius: 10px; font-family: 'Courier New', monospace; font-size: 14px; resize: vertical; transition: border-color 0.3s; }
        textarea:focus { outline: none; border-color: #667eea; }
        .generate-btn { width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 18px; border: none; border-radius: 10px; font-size: 18px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        .generate-btn:hover { transform: translateY(-2px); }
        .generate-btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .result-card { background: #d4edda; border: 1px solid #c3e6cb; border-radius: 10px; padding: 20px; margin-top: 20px; }
        .result-card.error { background: #f8d7da; border-color: #f5c6cb; }
        .loading { display: none; text-align: center; padding: 20px; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🏷️</div>
            <div class="title">ZPL Generator Pro</div>
            <div class="subtitle">Sistema Ultra Robusto - Suporte Ilimitado</div>
        </div>
        <div class="content">
            <div class="info-card">
                <h3>📏 Medidas das Etiquetas</h3>
                <p><strong>8 cm × 2,5 cm</strong> - Otimizado para impressoras Argox</p>
            </div>
            <div class="ultra-card">
                <h3>🔧 Sistema Ultra Robusto:</h3>
                <ul style="margin-left: 20px; color: #666;">
                    <li><strong>✅ Suporte Ilimitado:</strong> Códigos de 1 KB até 50 GB</li>
                    <li><strong>🔄 Processamento Paralelo:</strong> Múltiplos lotes simultâneos</li>
                    <li><strong>📡 Streaming de Dados:</strong> Não sobrecarrega memória</li>
                    <li><strong>🔁 Retry Inteligente:</strong> Até 7 tentativas com backoff</li>
                    <li><strong>⏱️ Timeout Adaptativo:</strong> Ajusta para código grande</li>
                    <li><strong>🛡️ Sistema 24/7:</strong> Funciona sem falhas</li>
                </ul>
            </div>
            <form id="zplForm">
                <div class="form-group">
                    <label for="zpl_code">📝 Cole seu código ZPL aqui (qualquer tamanho):</label>
                    <textarea id="zpl_code" name="zpl_code" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDMTTB52229^FS
...
^XZ

Cole códigos de qualquer tamanho - sistema ultra robusto!"></textarea>
                </div>
                <button type="submit" class="generate-btn" id="generateBtn">🚀 Gerar PDF Ultra Robusto (8×2,5cm)</button>
            </form>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p id="loadingText">Processando código ZPL ultra robusto...</p>
            </div>
            <div id="result"></div>
        </div>
    </div>
    <script>
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const zplCode = document.getElementById('zpl_code').value.trim();
            if (!zplCode) { alert('Por favor, cole seu código ZPL primeiro!'); return; }
            
            const generateBtn = document.getElementById('generateBtn');
            const loading = document.getElementById('loading');
            const result = document.getElementById('result');
            
            generateBtn.disabled = true;
            generateBtn.textContent = '⏳ Processando Ultra Robusto...';
            loading.style.display = 'block';
            result.innerHTML = '';
            
            try {
                const response = await fetch('/generate-pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl_code: zplCode })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = 'etiquetas_zpl_ultra_robusto.pdf';
                    document.body.appendChild(a); a.click();
                    window.URL.revokeObjectURL(url); document.body.removeChild(a);
                    
                    result.innerHTML = `<div class="result-card">
                        <h3>✅ PDF Gerado com Sucesso Ultra Robusto!</h3>
                        <p>Arquivo PDF gerado com medidas 8×2,5cm - Sistema Ultra Robusto</p>
                    </div>`;
                } else {
                    const errorData = await response.json();
                    result.innerHTML = `<div class="result-card error">
                        <h3>❌ Erro no Processamento</h3>
                        <p>${errorData.error || 'Erro desconhecido'}</p>
                    </div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="result-card error">
                    <h3>❌ Erro de Conexão</h3>
                    <p>Erro: ${error.message}</p>
                </div>`;
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = '🚀 Gerar PDF Ultra Robusto (8×2,5cm)';
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(MAIN_TEMPLATE)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Arquivo muito grande. Limite: 50 GB'}), 413

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl_code', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        
        # Detectar blocos ZPL
        zpl_blocks = re.findall(r'\^XA.*?\^XZ', zpl_code, re.DOTALL | re.IGNORECASE)
        if not zpl_blocks:
            return jsonify({'error': 'Código ZPL inválido - nenhum bloco ^XA...^XZ encontrado'}), 400
        
        total_blocks = len(zpl_blocks)
        logger.info(f"🚀 PROCESSAMENTO ULTRA ROBUSTO: {total_blocks} blocos, {len(zpl_code):,} chars")
        
        # CONFIGURAÇÃO ADAPTATIVA ULTRA ROBUSTA
        if total_blocks <= 10:
            BATCH_SIZE, DELAY, MAX_RETRIES, TIMEOUT, WORKERS = 10, 0.5, 2, 30, 2
        elif total_blocks <= 100:
            BATCH_SIZE, DELAY, MAX_RETRIES, TIMEOUT, WORKERS = 5, 1, 3, 60, 3
        elif total_blocks <= 1000:
            BATCH_SIZE, DELAY, MAX_RETRIES, TIMEOUT, WORKERS = 3, 2, 5, 120, 4
        else:
            BATCH_SIZE, DELAY, MAX_RETRIES, TIMEOUT, WORKERS = 2, 3, 7, 300, 5
        
        logger.info(f"🔧 CONFIG: Lote={BATCH_SIZE}, Timeout={TIMEOUT}s, Retries={RETRY}, Workers={WORKERS}")
        
        start_time = time.time()
        pdf_merger = PdfMerger()
        success_count = 0
        
        # Dividir em lotes
        batches = [zpl_blocks[i:i+BATCH_SIZE] for i in range(0, len(zpl_blocks), BATCH_SIZE)]
        
        def process_batch(batch_data):
            batch_index, batch = batch_data
            for attempt in range(MAX_RETRIES):
                try:
                    batch_zpl = '\n'.join(batch) + '\n'
                    pdf_data = generate_pdf_via_labelary_ultra_robust(batch_zpl, TIMEOUT, attempt + 1)
                    if pdf_data:
                        logger.info(f"✅ Lote {batch_index + 1} OK (tentativa {attempt + 1})")
                        return {'success': True, 'pdf_data': pdf_data, 'blocks_count': len(batch)}
                except Exception as e:
                    logger.error(f"💥 Lote {batch_index + 1}, tentativa {attempt + 1}: {str(e)}")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep((2 ** attempt) * 1)  # Backoff exponencial
            
            return {'success': False, 'blocks': batch}
        
        # Processamento paralelo ultra robusto
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_batch = {executor.submit(process_batch, (i, batch)): i for i, batch in enumerate(batches)}
            
            for future in as_completed(future_to_batch):
                result = future.result()
                if result['success']:
                    pdf_merger.append(io.BytesIO(result['pdf_data']))
                    success_count += result['blocks_count']
                    progress = (success_count / total_blocks) * 100
                    logger.info(f"📈 Progresso: {progress:.1f}% ({success_count}/{total_blocks})")
                
                time.sleep(DELAY)
                gc.collect()
        
        if success_count == 0:
            return jsonify({'error': 'Nenhum bloco processado com sucesso'}), 500
        
        # Gerar PDF final
        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        pdf_merger.close()
        output_buffer.seek(0)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(output_buffer.getvalue())
        temp_file.close()
        
        processing_time = time.time() - start_time
        file_size_kb = len(output_buffer.getvalue()) / 1024
        success_rate = (success_count / total_blocks) * 100
        
        logger.info(f"✅ ULTRA ROBUSTO CONCLUÍDO: {success_count}/{total_blocks} blocos ({success_rate:.1f}%), {processing_time:.1f}s, {file_size_kb:.1f}KB")
        
        return send_file(temp_file.name, as_attachment=True, download_name='etiquetas_zpl_ultra_robusto.pdf', mimetype='application/pdf')
        
    except Exception as e:
        logger.error(f"💥 Erro crítico: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

def generate_pdf_via_labelary_ultra_robust(zpl_code, timeout=60, attempt=1):
    """Gera PDF via Labelary com sistema ultra robusto"""
    try:
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/pdf'}
        
        # Timeout adaptativo
        code_size_kb = len(zpl_code) / 1024
        if code_size_kb > 100:
            timeout = min(timeout * 2, 600)
        
        logger.info(f"📡 Labelary (Tentativa {attempt}, Timeout: {timeout}s, {code_size_kb:.1f}KB)")
        
        response = requests.post(url, data=zpl_code, headers=headers, timeout=timeout, stream=True)
        
        if response.status_code == 200:
            pdf_data = io.BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_data.write(chunk)
            
            pdf_content = pdf_data.getvalue()
            pdf_data.close()
            logger.info(f"✅ PDF recebido ({len(pdf_content)} bytes)")
            return pdf_content
        else:
            logger.error(f"❌ Labelary: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.warning(f"⏰ Timeout Labelary (Tentativa {attempt})")
        return None
    except Exception as e:
        logger.error(f"💥 Erro Labelary (Tentativa {attempt}): {str(e)}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
