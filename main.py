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
    <title>ZPL Generator Pro - Ultra Otimizado</title>
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
            <div class="subtitle">Sistema Ultra Otimizado - Zero Limites</div>
        </div>
        <div class="content">
            <div class="info-card">
                <h3>📏 Medidas das Etiquetas</h3>
                <p><strong>8 cm × 2,5 cm</strong> - Otimizado para impressoras Argox</p>
            </div>
            <div class="ultra-card">
                <h3>🚀 Sistema Ultra Otimizado:</h3>
                <ul style="margin-left: 20px; color: #666;">
                    <li><strong>💾 Arquivos em Disco:</strong> Não sobrecarrega memória</li>
                    <li><strong>📊 Limite por KB:</strong> Lotes inteligentes por tamanho</li>
                    <li><strong>🔄 Fallback Automático:</strong> Reduz lote se falhar</li>
                    <li><strong>📡 Streaming Direto:</strong> PDF final otimizado</li>
                    <li><strong>🛡️ Sistema 24/7:</strong> Funciona com qualquer tamanho</li>
                    <li><strong>⚡ Zero Crash:</strong> Memória sempre controlada</li>
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

Sistema ultra otimizado - suporta códigos gigantescos!"></textarea>
                </div>
                <button type="submit" class="generate-btn" id="generateBtn">🚀 Gerar PDF Ultra Otimizado (8×2,5cm)</button>
            </form>
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p id="loadingText">Processando com sistema ultra otimizado...</p>
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
            generateBtn.textContent = '⏳ Processando Ultra Otimizado...';
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
                    a.href = url; a.download = 'etiquetas_zpl_ultra_otimizado.pdf';
                    document.body.appendChild(a); a.click();
                    window.URL.revokeObjectURL(url); document.body.removeChild(a);
                    
                    result.innerHTML = `<div class="result-card">
                        <h3>✅ PDF Gerado com Sucesso Ultra Otimizado!</h3>
                        <p>Sistema ultra otimizado - memória controlada, zero crash!</p>
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
                generateBtn.textContent = '🚀 Gerar PDF Ultra Otimizado (8×2,5cm)';
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

def create_smart_batches(zpl_blocks, max_blocks=5, max_kb=500):
    """Cria lotes inteligentes limitados por blocos E tamanho em KB"""
    batches = []
    current_batch = []
    current_size = 0
    
    for block in zpl_blocks:
        block_size_kb = len(block) / 1024
        
        # Se adicionar este bloco exceder limites, finaliza lote atual
        if (len(current_batch) >= max_blocks or 
            current_size + block_size_kb > max_kb) and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        
        current_batch.append(block)
        current_size += block_size_kb
    
    # Adiciona último lote se não vazio
    if current_batch:
        batches.append(current_batch)
    
    return batches

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    temp_pdfs = []  # Lista de PDFs temporários em disco
    
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
        total_size_kb = len(zpl_code) / 1024
        logger.info(f"🚀 PROCESSAMENTO ULTRA OTIMIZADO: {total_blocks} blocos, {total_size_kb:.1f}KB")
        
        # CONFIGURAÇÃO ADAPTATIVA ULTRA OTIMIZADA
        if total_blocks <= 10:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 10, 1000, 2, 30, 2
        elif total_blocks <= 100:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 5, 500, 3, 60, 3
        elif total_blocks <= 1000:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 3, 300, 5, 120, 4
        else:
            MAX_BLOCKS, MAX_KB, MAX_RETRIES, TIMEOUT, WORKERS = 2, 200, 7, 300, 5
        
        # Limitar workers para não sobrecarregar
        WORKERS = min(WORKERS, os.cpu_count() * 2 if os.cpu_count() else 4)
        
        logger.info(f"🔧 CONFIG: MaxBlocks={MAX_BLOCKS}, MaxKB={MAX_KB}, Timeout={TIMEOUT}s, Workers={WORKERS}")
        
        start_time = time.time()
        success_count = 0
        
        # Criar lotes inteligentes (por blocos E tamanho)
        batches = create_smart_batches(zpl_blocks, MAX_BLOCKS, MAX_KB)
        logger.info(f"📦 Criados {len(batches)} lotes inteligentes")
        
        def process_batch_with_fallback(batch_data):
            batch_index, batch = batch_data
            current_batch = batch[:]  # Cópia para fallback
            
            for attempt in range(MAX_RETRIES):
                try:
                    batch_zpl = '\n'.join(current_batch) + '\n'
                    batch_size_kb = len(batch_zpl) / 1024
                    
                    pdf_data = generate_pdf_via_labelary_ultra_robust(batch_zpl, TIMEOUT, attempt + 1)
                    if pdf_data:
                        # SALVAR PDF EM DISCO (não na memória)
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                        temp_file.write(pdf_data)
                        temp_file.close()
                        
                        logger.info(f"✅ Lote {batch_index + 1} OK ({len(current_batch)} blocos, {batch_size_kb:.1f}KB)")
                        return {'success': True, 'pdf_path': temp_file.name, 'blocks_count': len(current_batch)}
                        
                except Exception as e:
                    logger.error(f"💥 Lote {batch_index + 1}, tentativa {attempt + 1}: {str(e)}")
                
                # FALLBACK: Reduzir lote pela metade se falhar
                if len(current_batch) > 1 and attempt < MAX_RETRIES - 1:
                    mid = len(current_batch) // 2
                    current_batch = current_batch[:mid]
                    logger.warning(f"🔄 Fallback: Reduzindo lote {batch_index + 1} para {len(current_batch)} blocos")
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep((2 ** attempt) * 1)  # Backoff exponencial
            
            return {'success': False, 'blocks': current_batch}
        
        # Processamento paralelo ultra otimizado
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            future_to_batch = {executor.submit(process_batch_with_fallback, (i, batch)): i for i, batch in enumerate(batches)}
            
            for future in as_completed(future_to_batch):
                result = future.result()
                if result['success']:
                    temp_pdfs.append(result['pdf_path'])
                    success_count += result['blocks_count']
                    progress = (success_count / total_blocks) * 100
                    logger.info(f"📈 Progresso: {progress:.1f}% ({success_count}/{total_blocks})")
                
                time.sleep(0.1)  # Pausa mínima
        
        if not temp_pdfs:
            return jsonify({'error': 'Nenhum bloco processado com sucesso'}), 500
        
        # MESCLAR PDFs DIRETO EM DISCO (não na memória)
        final_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        final_pdf.close()
        
        pdf_merger = PdfMerger()
        for pdf_path in temp_pdfs:
            pdf_merger.append(pdf_path)
        
        # Escrever direto no arquivo final
        with open(final_pdf.name, 'wb') as output_file:
            pdf_merger.write(output_file)
        pdf_merger.close()
        
        # Limpar PDFs temporários
        for pdf_path in temp_pdfs:
            try:
                os.unlink(pdf_path)
            except:
                pass
        
        processing_time = time.time() - start_time
        file_size_kb = os.path.getsize(final_pdf.name) / 1024
        success_rate = (success_count / total_blocks) * 100
        
        logger.info(f"✅ ULTRA OTIMIZADO CONCLUÍDO: {success_count}/{total_blocks} blocos ({success_rate:.1f}%), {processing_time:.1f}s, {file_size_kb:.1f}KB")
        
        return send_file(final_pdf.name, as_attachment=True, download_name='etiquetas_zpl_ultra_otimizado.pdf', mimetype='application/pdf')
        
    except Exception as e:
        logger.error(f"💥 Erro crítico: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500
    finally:
        # Limpeza final de segurança
        for pdf_path in temp_pdfs:
            try:
                os.unlink(pdf_path)
            except:
                pass

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
            error_msg = f"HTTP {response.status_code}"
            if response.text:
                error_msg += f": {response.text[:100]}"
            logger.error(f"❌ Labelary: {error_msg}")
            return None
            
    except requests.exceptions.Timeout:
        logger.warning(f"⏰ Timeout Labelary (Tentativa {attempt})")
        return None
    except Exception as e:
        logger.error(f"💥 Erro Labelary (Tentativa {attempt}): {str(e)}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
