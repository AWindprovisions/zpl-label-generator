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
    <title>ZPL Generator - Código do Produto</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .final-card { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .fixes { background: #fff3cd; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107; }
        .fix-item { display: flex; align-items: center; margin: 10px 0; }
        .fix-icon { font-size: 20px; margin-right: 10px; }
        textarea { width: 100%; height: 200px; padding: 15px; font-family: monospace; border: 2px solid #e9ecef; border-radius: 8px; }
        button { width: 100%; padding: 20px; font-size: 18px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; border: none; border-radius: 8px; cursor: pointer; margin: 10px 0; font-weight: bold; }
        button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }
        .result { margin-top: 20px; padding: 20px; border-radius: 8px; }
        .success { background: linear-gradient(135deg, #00b894 0%, #00cec9 100%); color: white; }
        .error { background: linear-gradient(135deg, #d63031 0%, #e17055 100%); color: white; }
        .processing { background: linear-gradient(135deg, #0984e3 0%, #6c5ce7 100%); color: white; }
        .progress-container { display: none; margin-top: 20px; }
        .progress { background: #e9ecef; border-radius: 10px; height: 30px; margin: 15px 0; overflow: hidden; }
        .progress-bar { background: linear-gradient(90deg, #ff6b6b 0%, #ee5a24 100%); height: 100%; border-radius: 10px; transition: width 0.5s ease; width: 0%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }
        .stats { background: white; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ff6b6b; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .stat-item { text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #ff6b6b; }
        .stat-label { font-size: 12px; color: #6c757d; text-transform: uppercase; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #ff6b6b; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .phase { background: #fff; padding: 10px 15px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #ff6b6b; }
        .phase.active { border-left-color: #ffc107; background: #fff3cd; }
        .phase.completed { border-left-color: #00b894; background: #d1f2eb; }
        .debug-info { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Detecção por Código do Produto</p>
    </div>
    
    <div class="final-card">
        <h2>🎯 Detecção Corrigida</h2>
        <p><strong>Código do produto</strong> • <strong>VGYP85662 → KYFI92509</strong> • <strong>Separadores precisos</strong></p>
    </div>
    
    <div class="fixes">
        <h3>🔧 Nova Detecção:</h3>
        <div class="fix-item">
            <div class="fix-icon">🎯</div>
            <div><strong>Código do Produto:</strong> Segunda linha (VGYP85662, KYFI92509, etc.)</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">📊</div>
            <div><strong>Múltiplos Padrões:</strong> ^FD, ^A0, texto após código de barras</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">📏</div>
            <div><strong>Separador Preciso:</strong> Apenas quando código do produto muda</div>
        </div>
        <div class="fix-item">
            <div class="fix-icon">🔍</div>
            <div><strong>Debug Detalhado:</strong> Mostra cada código detectado</div>
        </div>
    </div>
    
    <form id="zplForm">
        <label for="zplCode"><strong>Cole seu código ZPL (detecção por código do produto):</strong></label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDVGYP85662^FS
^FO105,75^A0N,20,25^FH^FDVGYP85662^FS
^XZ

Agora detecta VGYP85662 → KYFI92509 corretamente!"></textarea><br><br>
        <button type="submit">🎯 Gerar PDF com Código do Produto</button>
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
            <div class="phase" id="phase1">🔍 Fase 1: Analisando códigos do produto</div>
            <div class="phase" id="phase2">📏 Fase 2: Detectando mudanças VGYP→KYFI</div>
            <div class="phase" id="phase3">⚡ Fase 3: Processando com separadores</div>
            <div class="phase" id="phase4">📄 Fase 4: Mesclando PDF único</div>
            <div class="phase" id="phase5">✅ Fase 5: PDF com separadores precisos</div>
        </div>
        
        <div class="debug-info" id="debugInfo" style="display: none;">
            <strong>🔍 Debug - Códigos Detectados:</strong><br>
            <div id="debugContent"></div>
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
            
            // Mostrar debug se disponível
            if (data.debug_info) {
                document.getElementById('debugInfo').style.display = 'block';
                document.getElementById('debugContent').innerHTML = data.debug_info.join('<br>');
            }
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
                                    <h3>🎉 PDF com Separadores Precisos!</h3>
                                    <p><strong>${data.total_blocks} blocos processados</strong> em ${((Date.now() - startTime) / 1000).toFixed(1)} segundos</p>
                                    <p>📏 <strong>${data.separators_added || 0} separadores</strong> entre códigos diferentes</p>
                                    <p>🎯 <strong>Detecção por código do produto</strong> - VGYP85662 → KYFI92509</p>
                                    <button onclick="downloadPdf('${processingId}')" style="margin-top: 15px;">
                                        📥 Baixar PDF com Separadores Precisos
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
                        document.querySelector('button[type="submit"]').textContent = '🎯 Gerar PDF com Código do Produto';
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
            button.textContent = '⏳ Detectando códigos do produto...';
            progressContainer.style.display = 'block';
            result.innerHTML = '';
            
            startTime = Date.now();
            updatePhase(1);
            
            try {
                const response = await fetch('/generate-product-code', {
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
                button.textContent = '🎯 Gerar PDF com Código do Produto';
                progressContainer.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

def extract_product_code_from_block(zpl_block):
    """Extrai código do produto (segunda linha) do bloco ZPL"""
    # Padrões para encontrar o código do produto (não o código de barras)
    patterns = [
        # Padrão ^FD seguido de código alfanumérico (segunda ocorrência)
        r'\^FD([A-Za-z0-9]{6,12})\^FS',
        # Padrão ^A0 seguido de ^FD com código
        r'\^A0.*?\^FD([A-Za-z0-9]{6,12})\^FS',
        # Padrão específico para códigos como VGYP85662
        r'\^FD([A-Z]{4}[0-9]{5})\^FS',
        # Padrão mais geral para códigos mistos
        r'\^FD([A-Z]{2,4}[A-Z0-9]{4,8})\^FS'
    ]
    
    all_codes = []
    
    for pattern in patterns:
        matches = re.findall(pattern, zpl_block, re.IGNORECASE)
        all_codes.extend(matches)
    
    # Remover duplicatas mantendo ordem
    unique_codes = []
    for code in all_codes:
        if code not in unique_codes:
            unique_codes.append(code)
    
    # Retornar o segundo código encontrado (primeira é geralmente código de barras)
    if len(unique_codes) >= 2:
        return unique_codes[1].upper()  # Segunda ocorrência
    elif len(unique_codes) == 1:
        # Se só tem um, verificar se parece com código de produto
        code = unique_codes[0].upper()
        if len(code) >= 6 and any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
            return code
    
    return None

def extract_all_info_from_block(zpl_block):
    """Extrai todas as informações do bloco para debug"""
    all_fd_matches = re.findall(r'\^FD([^\\^]+)\^FS', zpl_block)
    product_code = extract_product_code_from_block(zpl_block)
    
    return {
        'product_code': product_code,
        'all_codes': all_fd_matches[:3],  # Primeiros 3 códigos
        'block_preview': zpl_block[:100] + "..." if len(zpl_block) > 100 else zpl_block
    }

def create_product_separator(old_code, new_code):
    """Cria separador entre códigos de produto diferentes"""
    return f"""^XA
^LH0,0
^FO0,0^GB800,250,3^FS
^FO400,60^A0N,18,18^FH^FD=== MUDANÇA DE PRODUTO ===^FS
^FO400,100^A0N,14,14^FH^FDAnterior: {old_code or 'N/A'}^FS
^FO400,130^A0N,14,14^FH^FDNovo: {new_code or 'N/A'}^FS
^FO400,170^A0N,12,12^FH^FD--- SEPARADOR ---^FS
^XZ"""

@app.route('/generate-product-code', methods=['POST'])
def generate_product_code():
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
            'pdf_path': None,
            'debug_info': []
        }
        
        # Iniciar processamento em thread separada
        thread = threading.Thread(target=process_product_code_async, args=(processing_id, zpl_code))
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
    
    return send_file(status['pdf_path'], as_attachment=True, download_name='etiquetas_codigo_produto.pdf')

def process_product_code_async(processing_id, zpl_code):
    """Processa com detecção por código do produto"""
    try:
        status = processing_status[processing_id]
        debug_info = []
        
        # Fase 1: Analisar códigos do produto
        status.update({
            'status': 'Analisando códigos do produto...',
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
        
        # Fase 2: Detectar mudanças de código do produto
        status.update({
            'status': 'Detectando mudanças de código do produto...',
            'phase': 2
        })
        
        blocks_with_separators = []
        last_product_code = None
        separators_added = 0
        
        debug_info.append("🔍 === ANÁLISE DE CÓDIGOS DO PRODUTO ===")
        
        for i, block in enumerate(zpl_blocks):
            block_info = extract_all_info_from_block(block)
            current_product_code = block_info['product_code']
            
            debug_line = f"📦 Bloco {i+1}: {current_product_code or 'N/A'} | Todos: {block_info['all_codes']}"
            debug_info.append(debug_line)
            print(debug_line)
            
            # Se mudou de código do produto, adicionar separador
            if (last_product_code is not None and 
                current_product_code is not None and
                current_product_code != last_product_code):
                
                change_line = f"🔄 MUDANÇA: {last_product_code} → {current_product_code}"
                debug_info.append(change_line)
                print(change_line)
                
                separator = create_product_separator(last_product_code, current_product_code)
                blocks_with_separators.append(separator)
                separators_added += 1
            
            blocks_with_separators.append(block)
            if current_product_code:
                last_product_code = current_product_code
        
        final_line = f"✅ Total de separadores: {separators_added}"
        debug_info.append(final_line)
        print(final_line)
        
        status.update({
            'separators_added': separators_added,
            'debug_info': debug_info
        })
        
        # Fase 3: Processar lotes
        status.update({
            'status': 'Processando lotes com separadores...',
            'phase': 3
        })
        
        pdf_merger = PdfMerger()
        temp_files = []
        
        batch_size = 5
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
                    if attempt == 2:
                        print(f"Erro no lote {batch_num}: {str(e)}")
                
                if attempt < 2:
                    time.sleep(1)
            
            if not success:
                print(f"Lote {batch_num} falhou após 3 tentativas")
            
            time.sleep(0.5)
        
        # Fase 4: Mesclar PDFs
        status.update({
            'status': 'Mesclando PDFs...',
            'phase': 4,
            'processed_blocks': len(blocks_with_separators)
        })
        
        if not temp_files:
            raise Exception('Nenhum lote processado com sucesso')
        
        # Fase 5: Finalizar
        status.update({
            'status': 'Finalizando PDF com separadores precisos...',
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
            'status': f'PDF com separadores precisos! {separators_added} mudanças detectadas.',
            'phase': 5,
            'pdf_path': final_temp.name
        })
        
        print(f"🎉 PDF FINAL: {len(zpl_blocks)} blocos + {separators_added} separadores por código do produto")
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        status.update({
            'completed': True,
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
