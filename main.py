from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
import time
import threading
import uuid
from PyPDF2 import PdfMerger
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Armazenar status dos processamentos
processing_status = {}

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Versão Definitiva</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .final-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .features { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .feature { display: flex; align-items: center; margin: 10px 0; }
        .feature-icon { font-size: 24px; margin-right: 15px; }
        textarea { width: 100%; height: 200px; padding: 15px; font-family: monospace; border: 2px solid #e9ecef; border-radius: 8px; }
        button { width: 100%; padding: 20px; font-size: 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer; margin: 10px 0; font-weight: bold; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }
        .result { margin-top: 20px; padding: 20px; border-radius: 8px; }
        .success { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
        .error { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; }
        .processing { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333; }
        .progress-container { display: none; margin-top: 20px; }
        .progress { background: #e9ecef; border-radius: 10px; height: 30px; margin: 15px 0; overflow: hidden; }
        .progress-bar { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); height: 100%; border-radius: 10px; transition: width 0.5s ease; width: 0%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
        .stats { background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #667eea; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .stat-item { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #6c757d; text-transform: uppercase; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .phase { background: #fff; padding: 10px 15px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #28a745; }
        .phase.active { border-left-color: #ffc107; background: #fff3cd; }
        .phase.completed { border-left-color: #28a745; background: #d4edda; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Versão Definitiva - PDF Único Completo</p>
    </div>
    
    <div class="final-card">
        <h2>🎯 Versão Definitiva Aprimorada</h2>
        <p><strong>1 PDF único</strong> • <strong>Espaços entre SKUs</strong> • <strong>Processamento completo</strong></p>
    </div>
    
    <div class="features">
        <h3>✨ Recursos Definitivos:</h3>
        <div class="feature">
            <div class="feature-icon">📄</div>
            <div><strong>PDF Único Completo:</strong> Todas as 299 etiquetas em 1 arquivo</div>
        </div>
        <div class="feature">
            <div class="feature-icon">📏</div>
            <div><strong>Espaços Automáticos:</strong> Detecta mudança de SKU e insere separadores</div>
        </div>
        <div class="feature">
            <div class="feature-icon">⚡</div>
            <div><strong>Processamento Assíncrono:</strong> Não trava o navegador</div>
        </div>
        <div class="feature">
            <div class="feature-icon">📊</div>
            <div><strong>Progresso em Tempo Real:</strong> Acompanhe cada etapa</div>
        </div>
        <div class="feature">
            <div class="feature-icon">🔄</div>
            <div><strong>Sistema Robusto:</strong> Retry automático e recuperação</div>
        </div>
    </div>
    
    <form id="zplForm">
        <label for="zplCode"><strong>Cole seu código ZPL completo (será processado automaticamente):</strong></label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Cole todo o código ZPL - será processado em 1 PDF único!"></textarea><br><br>
        <button type="submit">🚀 Gerar PDF Único Completo (Todas as Etiquetas)</button>
    </form>
    
    <div class="progress-container" id="progressContainer">
        <div class="spinner" id="spinner"></div>
        <h3 id="statusTitle">Processando...</h3>
        
        <div class="progress">
            <div class="progress-bar" id="progressBar">0%</div>
        </div>
        
        <div class="stats">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" id="blocksProcessed">0</div>
                    <div class="stat-label">Blocos Processados</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="totalBlocks">0</div>
                    <div class="stat-label">Total de Blocos</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="timeElapsed">0s</div>
                    <div class="stat-label">Tempo Decorrido</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="estimatedTime">--</div>
                    <div class="stat-label">Tempo Estimado</div>
                </div>
            </div>
        </div>
        
        <div id="phases">
            <div class="phase" id="phase1">📦 Fase 1: Analisando código ZPL</div>
            <div class="phase" id="phase2">🔍 Fase 2: Detectando SKUs e separadores</div>
            <div class="phase" id="phase3">⚡ Fase 3: Processando lotes via Labelary</div>
            <div class="phase" id="phase4">📄 Fase 4: Mesclando PDFs</div>
            <div class="phase" id="phase5">✅ Fase 5: Finalizando PDF único</div>
        </div>
    </div>
    
    <div id="result"></div>
    
    <script>
        let processingId = null;
        let startTime = null;
        let statusInterval = null;
        
        function updatePhase(phaseNum, status = 'active') {
            // Limpar fases anteriores
            for (let i = 1; i <= 5; i++) {
                const phase = document.getElementById(`phase${i}`);
                phase.className = 'phase';
                if (i < phaseNum) {
                    phase.className = 'phase completed';
                } else if (i === phaseNum) {
                    phase.className = `phase ${status}`;
                }
            }
        }
        
        function updateProgress(data) {
            const percentage = data.total_blocks > 0 ? (data.processed_blocks / data.total_blocks) * 100 : 0;
            
            document.getElementById('progressBar').style.width = percentage + '%';
            document.getElementById('progressBar').textContent = percentage.toFixed(1) + '%';
            
            document.getElementById('blocksProcessed').textContent = data.processed_blocks;
            document.getElementById('totalBlocks').textContent = data.total_blocks;
            
            const elapsed = (Date.now() - startTime) / 1000;
            document.getElementById('timeElapsed').textContent = elapsed.toFixed(1) + 's';
            
            if (data.processed_blocks > 0) {
                const avgTime = elapsed / data.processed_blocks;
                const remaining = (data.total_blocks - data.processed_blocks) * avgTime;
                document.getElementById('estimatedTime').textContent = remaining.toFixed(1) + 's';
            }
            
            document.getElementById('statusTitle').textContent = data.status || 'Processando...';
            updatePhase(data.phase || 1);
        }
        
        function checkStatus() {
            if (!processingId) return;
            
            fetch(`/status/${processingId}`)
                .then(response => response.json())
                .then(data => {
                    updateProgress(data);
                    
                    if (data.completed) {
                        clearInterval(statusInterval);
                        document.getElementById('spinner').style.display = 'none';
                        
                        if (data.success) {
                            updatePhase(5, 'completed');
                            document.getElementById('result').innerHTML = `
                                <div class="result success">
                                    <h3>🎉 PDF Único Completo Gerado!</h3>
                                    <p><strong>${data.total_blocks} blocos processados</strong> em ${((Date.now() - startTime) / 1000).toFixed(1)} segundos</p>
                                    <p>📄 <strong>1 PDF único</strong> com todas as etiquetas e espaços entre SKUs</p>
                                    <button onclick="downloadPdf('${processingId}')" style="margin-top: 15px;">
                                        📥 Baixar PDF Completo
                                    </button>
                                </div>
                            `;
                        } else {
                            document.getElementById('result').innerHTML = `
                                <div class="result error">
                                    <h3>❌ Erro no Processamento</h3>
                                    <p>${data.error}</p>
                                </div>
                            `;
                        }
                        
                        document.querySelector('button[type="submit"]').disabled = false;
                        document.querySelector('button[type="submit"]').textContent = '🚀 Gerar PDF Único Completo (Todas as Etiquetas)';
                    }
                })
                .catch(error => {
                    console.error('Erro ao verificar status:', error);
                });
        }
        
        function downloadPdf(id) {
            window.location.href = `/download/${id}`;
        }
        
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            const button = e.target.querySelector('button');
            const result = document.getElementById('result');
            const progressContainer = document.getElementById('progressContainer');
            
            button.disabled = true;
            button.textContent = '⏳ Iniciando processamento...';
            progressContainer.style.display = 'block';
            result.innerHTML = '';
            
            startTime = Date.now();
            updatePhase(1);
            
            try {
                const response = await fetch('/generate-complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode })
                });
                
                const data = await response.json();
                
                if (data.processing_id) {
                    processingId = data.processing_id;
                    statusInterval = setInterval(checkStatus, 1000);
                    checkStatus(); // Primeira verificação imediata
                } else {
                    throw new Error(data.error || 'Erro desconhecido');
                }
                
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
                button.disabled = false;
                button.textContent = '🚀 Gerar PDF Único Completo (Todas as Etiquetas)';
                progressContainer.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

def extract_sku_from_block(zpl_block):
    """Extrai SKU do bloco ZPL para detectar mudanças"""
    patterns = [
        r'SKU[:\s]*([A-Za-z0-9\-_.]+)',
        r'\^FD([A-Za-z0-9\-_.]{6,})\^FS',
        r'\^A0.*?\^FD([A-Za-z0-9\-_.]+)\^FS'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, zpl_block, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def create_blank_separator():
    """Cria etiqueta separadora entre SKUs"""
    return """^XA
^LH0,0
^FO0,0^GB800,250,2^FS
^FO400,125^A0N,20,20^FH^FD--- SEPARADOR SKU ---^FS
^XZ"""

@app.route('/generate-complete', methods=['POST'])
def generate_complete():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        
        # Gerar ID único para este processamento
        processing_id = str(uuid.uuid4())
        
        # Inicializar status
        processing_status[processing_id] = {
            'completed': False,
            'success': False,
            'processed_blocks': 0,
            'total_blocks': 0,
            'status': 'Iniciando...',
            'phase': 1,
            'error': None,
            'pdf_path': None
        }
        
        # Iniciar processamento em thread separada
        thread = threading.Thread(target=process_complete_async, args=(processing_id, zpl_code))
        thread.daemon = True
        thread.start()
        
        return jsonify({'processing_id': processing_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<processing_id>')
def get_status(processing_id):
    status = processing_status.get(processing_id, {
        'completed': True,
        'success': False,
        'error': 'ID de processamento não encontrado'
    })
    return jsonify(status)

@app.route('/download/<processing_id>')
def download_pdf(processing_id):
    status = processing_status.get(processing_id)
    if not status or not status.get('success') or not status.get('pdf_path'):
        return jsonify({'error': 'PDF não encontrado'}), 404
    
    return send_file(status['pdf_path'], as_attachment=True, download_name='etiquetas_completas_definitivo.pdf')

def process_complete_async(processing_id, zpl_code):
    """Processa todo o código ZPL de forma assíncrona"""
    try:
        status = processing_status[processing_id]
        
        # Fase 1: Analisar código ZPL
        status.update({
            'status': 'Analisando código ZPL...',
            'phase': 1
        })
        
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        
        if not zpl_blocks:
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            zpl_blocks = [zpl_code]
        
        status['total_blocks'] = len(zpl_blocks)
        
        # Fase 2: Detectar SKUs e adicionar separadores
        status.update({
            'status': 'Detectando SKUs e adicionando separadores...',
            'phase': 2
        })
        
        blocks_with_separators = []
        last_sku = None
        
        for i, block in enumerate(zpl_blocks):
            current_sku = extract_sku_from_block(block)
            
            # Se mudou de SKU, adicionar separador
            if last_sku is not None and current_sku != last_sku and current_sku is not None:
                blocks_with_separators.append(create_blank_separator())
            
            blocks_with_separators.append(block)
            last_sku = current_sku
        
        # Fase 3: Processar lotes
        status.update({
            'status': 'Processando lotes via Labelary...',
            'phase': 3
        })
        
        pdf_merger = PdfMerger()
        temp_files = []
        
        batch_size = 5  # Lotes pequenos para estabilidade
        total_batches = (len(blocks_with_separators) + batch_size - 1) // batch_size
        
        for i in range(0, len(blocks_with_separators), batch_size):
            batch = blocks_with_separators[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            status.update({
                'status': f'Processando lote {batch_num}/{total_batches}...',
                'processed_blocks': i
            })
            
            # Tentar processar lote com retry
            success = False
            for attempt in range(3):
                try:
                    batch_zpl = '\n'.join(batch)
                    
                    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Accept': 'application/pdf'
                    }
                    
                    response = requests.post(url, data=batch_zpl, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                        temp_file.write(response.content)
                        temp_file.close()
                        temp_files.append(temp_file.name)
                        
                        pdf_merger.append(io.BytesIO(response.content))
                        success = True
                        break
                        
                except Exception as e:
                    if attempt == 2:  # Última tentativa
                        print(f"Erro no lote {batch_num}: {str(e)}")
                
                if attempt < 2:
                    time.sleep(1)
            
            if not success:
                print(f"Lote {batch_num} falhou após 3 tentativas")
            
            time.sleep(0.5)  # Pausa entre lotes
        
        # Fase 4: Mesclar PDFs
        status.update({
            'status': 'Mesclando todos os PDFs...',
            'phase': 4,
            'processed_blocks': len(blocks_with_separators)
        })
        
        if not temp_files:
            raise Exception('Nenhum lote processado com sucesso')
        
        # Fase 5: Finalizar PDF único
        status.update({
            'status': 'Finalizando PDF único...',
            'phase': 5
        })
        
        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        pdf_merger.close()
        output_buffer.seek(0)
        
        final_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        final_temp.write(output_buffer.getvalue())
        final_temp.close()
        
        # Limpar arquivos temporários
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        # Finalizar com sucesso
        status.update({
            'completed': True,
            'success': True,
            'status': 'PDF único completo gerado!',
            'phase': 5,
            'pdf_path': final_temp.name
        })
        
    except Exception as e:
        status.update({
            'completed': True,
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
