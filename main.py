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
    <title>ZPL Generator - SKU Corrigido</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .final-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .fixes { background: #d4edda; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #28a745; }
        .fix-item { display: flex; align-items: center; margin: 10px 0; }
        .fix-icon { font-size: 20px; margin-right: 10px; }
        textarea { width: 100%; height: 200px; padding: 15px; font-family: monospace; border: 2px solid #e9ecef; border-radius: 8px; }
        button { width: 100%; padding: 20px; font-size: 18px; background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; border-radius: 8px; cursor: pointer; margin: 10px 0; font-weight: bold; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }
        .result { margin-top: 20px; padding: 20px; border-radius: 8px; }
        .success { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; }
        .error { background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); color: white; }
        .processing { background: linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%); color: white; }
        .progress-container { display: none; margin-top: 20px; }
        .progress { background: #e9ecef; border-radius: 10px; height: 30px; margin: 15px 0; overflow: hidden; }
        .progress-bar { background: linear-gradient(90deg, #28a745 0%, #20c997 100%); height: 100%; border-radius: 10px; transition: width 0.5s ease; width: 0%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
        .stats { background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .stat-item { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #28a745; }
        .stat-label { font-size: 12px; color: #6c757d; text-transform: uppercase; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #28a745; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
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
        <p>SKU Corrigido - Detecção Aprimorada</p>
    </div>
    
    <div class="final-card">
        <h2>🔧 Versão com SKU Corrigido</h2>
        <p><strong>Detecção por código de barras</strong> • <strong>Separadores precisos</strong> • <strong>PDF único</strong></p>
    </div>
    
    <div class="fixes">
        <h3>✅ Correções Aplicadas:</h3>
        <div class="fix-item">
            <div class="fix-icon">🔍</div>
            <div><strong>Detecção por Código de Barras:</strong> Usa primeira linha como referência principal</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">📏</div>
            <div><strong>Separadores Precisos:</strong> Apenas quando código de barras muda</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">🧹</div>
            <div><strong>Limpeza de Duplicatas:</strong> Remove separadores desnecessários</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">📊</div>
            <div><strong>Log Detalhado:</strong> Mostra exatamente onde separa</div>
        </div>
    </div>
    
    <form id="zplForm">
        <label for="zplCode"><strong>Cole seu código ZPL completo (detecção corrigida):</strong></label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Detecção corrigida - separadores precisos!"></textarea><br><br>
        <button type="submit">🔧 Gerar PDF com SKU Corrigido</button>
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
                    <div class="stat-value" id="separatorsAdded">0</div>
                    <div class="stat-label">Separadores Adicionados</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="timeElapsed">0s</div>
                    <div class="stat-label">Tempo Decorrido</div>
                </div>
            </div>
        </div>
        
        <div id="phases">
            <div class="phase" id="phase1">🔍 Fase 1: Analisando códigos de barras</div>
            <div class="phase" id="phase2">📏 Fase 2: Detectando mudanças de produto</div>
            <div class="phase" id="phase3">⚡ Fase 3: Processando com separadores</div>
            <div class="phase" id="phase4">📄 Fase 4: Mesclando PDF único</div>
            <div class="phase" id="phase5">✅ Fase 5: Finalizando com SKU corrigido</div>
        </div>
    </div>
    
    <div id="result"></div>
    
    <script>
        let processingId = null;
        let startTime = null;
        let statusInterval = null;
        
        function updatePhase(phaseNum, status = 'active') {
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
            document.getElementById('separatorsAdded').textContent = data.separators_added || 0;
            
            const elapsed = (Date.now() - startTime) / 1000;
            document.getElementById('timeElapsed').textContent = elapsed.toFixed(1) + 's';
            
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
                                    <h3>🎉 PDF com SKU Corrigido Gerado!</h3>
                                    <p><strong>${data.total_blocks} blocos processados</strong> em ${((Date.now() - startTime) / 1000).toFixed(1)} segundos</p>
                                    <p>📏 <strong>${data.separators_added || 0} separadores</strong> adicionados entre produtos diferentes</p>
                                    <p>🔍 <strong>Detecção por código de barras</strong> - Separadores precisos!</p>
                                    <button onclick="downloadPdf('${processingId}')" style="margin-top: 15px;">
                                        📥 Baixar PDF Corrigido
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
                        document.querySelector('button[type="submit"]').textContent = '🔧 Gerar PDF com SKU Corrigido';
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
            button.textContent = '⏳ Iniciando correção de SKU...';
            progressContainer.style.display = 'block';
            result.innerHTML = '';
            
            startTime = Date.now();
            updatePhase(1);
            
            try {
                const response = await fetch('/generate-corrected', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode })
                });
                
                const data = await response.json();
                
                if (data.processing_id) {
                    processingId = data.processing_id;
                    statusInterval = setInterval(checkStatus, 1000);
                    checkStatus();
                } else {
                    throw new Error(data.error || 'Erro desconhecido');
                }
                
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
                button.disabled = false;
                button.textContent = '🔧 Gerar PDF com SKU Corrigido';
                progressContainer.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

def extract_barcode_from_block(zpl_block):
    """Extrai código de barras do bloco ZPL (primeira linha de dados)"""
    # Procurar por padrões de código de barras
    patterns = [
        r'\^FD([A-Za-z0-9]+)\^FS',  # Padrão ^FD...^FS
        r'\^BCN.*?\^FD([A-Za-z0-9]+)\^FS',  # Código de barras específico
        r'\^BY.*?\^FD([A-Za-z0-9]+)\^FS'   # Outro padrão de código de barras
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, zpl_block, re.IGNORECASE)
        if matches:
            # Retornar o primeiro código encontrado (geralmente o código de barras)
            return matches[0].strip()
    
    return None

def extract_product_info(zpl_block):
    """Extrai informações do produto para debug"""
    barcode = extract_barcode_from_block(zpl_block)
    
    # Tentar extrair nome do produto (segunda linha geralmente)
    text_matches = re.findall(r'\^FD([^\\^]+)\^FS', zpl_block)
    product_name = text_matches[1] if len(text_matches) > 1 else "Produto desconhecido"
    
    return {
        'barcode': barcode,
        'product_name': product_name[:30] + "..." if len(product_name) > 30 else product_name
    }

def create_separator_with_info(old_product, new_product):
    """Cria separador com informações dos produtos"""
    return f"""^XA
^LH0,0
^FO0,0^GB800,250,2^FS
^FO400,50^A0N,16,16^FH^FD--- MUDANÇA DE PRODUTO ---^FS
^FO400,100^A0N,12,12^FH^FDAnterior: {old_product['barcode'] or 'N/A'}^FS
^FO400,130^A0N,12,12^FH^FDNovo: {new_product['barcode'] or 'N/A'}^FS
^FO400,180^A0N,10,10^FH^FD{old_product['product_name']}^FS
^FO400,200^A0N,10,10^FH^FD{new_product['product_name']}^FS
^XZ"""

@app.route('/generate-corrected', methods=['POST'])
def generate_corrected():
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
            'separators_added': 0,
            'status': 'Iniciando...',
            'phase': 1,
            'error': None,
            'pdf_path': None
        }
        
        # Iniciar processamento em thread separada
        thread = threading.Thread(target=process_corrected_async, args=(processing_id, zpl_code))
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
    
    return send_file(status['pdf_path'], as_attachment=True, download_name='etiquetas_sku_corrigido.pdf')

def process_corrected_async(processing_id, zpl_code):
    """Processa com detecção corrigida de SKU"""
    try:
        status = processing_status[processing_id]
        
        # Fase 1: Analisar códigos de barras
        status.update({
            'status': 'Analisando códigos de barras...',
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
        
        # Fase 2: Detectar mudanças de produto por código de barras
        status.update({
            'status': 'Detectando mudanças de produto...',
            'phase': 2
        })
        
        blocks_with_separators = []
        last_product = None
        separators_added = 0
        
        print(f"🔍 === ANÁLISE DE PRODUTOS ===")
        
        for i, block in enumerate(zpl_blocks):
            current_product = extract_product_info(block)
            
            print(f"📦 Bloco {i+1}: {current_product['barcode']} - {current_product['product_name']}")
            
            # Se mudou de código de barras, adicionar separador
            if (last_product is not None and 
                current_product['barcode'] is not None and 
                last_product['barcode'] is not None and
                current_product['barcode'] != last_product['barcode']):
                
                print(f"🔄 MUDANÇA DETECTADA: {last_product['barcode']} → {current_product['barcode']}")
                separator = create_separator_with_info(last_product, current_product)
                blocks_with_separators.append(separator)
                separators_added += 1
            
            blocks_with_separators.append(block)
            last_product = current_product
        
        print(f"✅ Total de separadores adicionados: {separators_added}")
        status['separators_added'] = separators_added
        
        # Fase 3: Processar lotes
        status.update({
            'status': 'Processando lotes com separadores...',
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
            'status': 'Mesclando PDFs com separadores...',
            'phase': 4,
            'processed_blocks': len(blocks_with_separators)
        })
        
        if not temp_files:
            raise Exception('Nenhum lote processado com sucesso')
        
        # Fase 5: Finalizar PDF único
        status.update({
            'status': 'Finalizando PDF com SKU corrigido...',
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
            'status': f'PDF corrigido gerado! {separators_added} separadores adicionados.',
            'phase': 5,
            'pdf_path': final_temp.name
        })
        
        print(f"🎉 PDF FINAL CORRIGIDO: {len(zpl_blocks)} blocos + {separators_added} separadores")
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        status.update({
            'completed': True,
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
