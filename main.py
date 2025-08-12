from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
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
    <title>ZPL Generator - Por Partes</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .strategy-card { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107; }
        .info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .controls { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        textarea { width: 100%; height: 200px; padding: 10px; font-family: monospace; }
        button { width: 100%; padding: 15px; font-size: 16px; background: #ffc107; color: #212529; border: none; border-radius: 5px; cursor: pointer; margin: 5px 0; }
        button:hover { background: #e0a800; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
        .loading { display: none; text-align: center; margin-top: 20px; }
        .spinner { border: 2px solid #f3f3f3; border-top: 2px solid #ffc107; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress { background: #f8f9fa; border-radius: 5px; margin: 10px 0; height: 20px; }
        .progress-bar { background: #ffc107; height: 100%; border-radius: 5px; transition: width 0.3s; width: 0%; }
        .stats { background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; font-size: 12px; }
        .range-input { width: 100%; margin: 10px 0; }
        label { display: block; margin: 5px 0; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Processamento por Partes - Evita Timeout</p>
    </div>
    
    <div class="strategy-card">
        <h3>💡 Estratégia Anti-Timeout:</h3>
        <ul>
            <li>📦 <strong>Processa 50 blocos por vez</strong> (evita timeout)</li>
            <li>⏱️ <strong>Tempo máximo:</strong> ~2 minutos por parte</li>
            <li>🔢 <strong>Para 299 blocos:</strong> 6 execuções de 50 blocos</li>
            <li>📁 <strong>PDFs separados:</strong> Depois você junta manualmente</li>
        </ul>
    </div>
    
    <div class="controls">
        <h3>🎛️ Controles de Processamento:</h3>
        <label for="startBlock">Bloco inicial (1-299):</label>
        <input type="number" id="startBlock" value="1" min="1" max="299" class="range-input">
        
        <label for="endBlock">Bloco final (1-299):</label>
        <input type="number" id="endBlock" value="50" min="1" max="299" class="range-input">
        
        <div style="margin: 10px 0;">
            <button onclick="setRange(1, 50)" class="btn-success">📦 Parte 1 (1-50)</button>
            <button onclick="setRange(51, 100)" class="btn-success">📦 Parte 2 (51-100)</button>
            <button onclick="setRange(101, 150)" class="btn-success">📦 Parte 3 (101-150)</button>
            <button onclick="setRange(151, 200)" class="btn-success">📦 Parte 4 (151-200)</button>
            <button onclick="setRange(201, 250)" class="btn-success">📦 Parte 5 (201-250)</button>
            <button onclick="setRange(251, 299)" class="btn-success">📦 Parte 6 (251-299)</button>
        </div>
    </div>
    
    <form id="zplForm">
        <label for="zplCode">Cole seu código ZPL completo (será processado por partes):</label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Cole todo o código - será processado por partes!"></textarea><br><br>
        <button type="submit">🚀 Processar Parte Selecionada</button>
    </form>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p id="loadingText">Processando parte...</p>
        <div class="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
        <p id="progressText">0% - Iniciando...</p>
        <div class="stats" id="stats">
            Blocos da parte: 0/0<br>
            Tempo decorrido: 0s
        </div>
    </div>
    
    <div id="result"></div>
    
    <script>
        function setRange(start, end) {
            document.getElementById('startBlock').value = start;
            document.getElementById('endBlock').value = end;
        }
        
        function updateProgress(processed, total, elapsed) {
            const percentage = total > 0 ? (processed / total) * 100 : 0;
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const stats = document.getElementById('stats');
            
            progressBar.style.width = percentage + '%';
            progressText.textContent = `${percentage.toFixed(1)}% - Processando...`;
            
            stats.innerHTML = `
                Blocos da parte: ${processed}/${total}<br>
                Tempo decorrido: ${elapsed.toFixed(1)}s
            `;
        }
        
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            const startBlock = parseInt(document.getElementById('startBlock').value);
            const endBlock = parseInt(document.getElementById('endBlock').value);
            
            if (startBlock > endBlock) {
                alert('Bloco inicial deve ser menor que o final!');
                return;
            }
            
            const button = e.target.querySelector('button');
            const result = document.getElementById('result');
            const loading = document.getElementById('loading');
            
            button.disabled = true;
            button.textContent = `⏳ Processando blocos ${startBlock}-${endBlock}...`;
            loading.style.display = 'block';
            result.innerHTML = '';
            
            const startTime = Date.now();
            
            try {
                const response = await fetch('/generate-part', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        zpl: zplCode,
                        start_block: startBlock,
                        end_block: endBlock
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `etiquetas_parte_${startBlock}-${endBlock}.pdf`;
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    const elapsed = (Date.now() - startTime) / 1000;
                    const blocksProcessed = endBlock - startBlock + 1;
                    
                    result.innerHTML = `<div class="result success">
                        <h3>✅ Parte ${startBlock}-${endBlock} Processada!</h3>
                        <p><strong>${blocksProcessed} blocos</strong> processados em ${elapsed.toFixed(1)} segundos</p>
                        <p>📁 PDF baixado: etiquetas_parte_${startBlock}-${endBlock}.pdf</p>
                        <p>🔄 <strong>Próximo:</strong> Ajuste os controles para a próxima parte</p>
                    </div>`;
                } else {
                    const error = await response.json();
                    result.innerHTML = `<div class="result error">❌ ${error.error}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
            } finally {
                button.disabled = false;
                button.textContent = '🚀 Processar Parte Selecionada';
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

@app.route('/generate-part', methods=['POST'])
def generate_part():
    try:
        print("🚀 === PROCESSAMENTO POR PARTES ===")
        
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        start_block = data.get('start_block', 1)
        end_block = data.get('end_block', 50)
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL não fornecido'}), 400
        
        # Detectar TODOS os blocos ZPL
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        
        if not zpl_blocks:
            return jsonify({'error': 'Nenhum bloco ZPL válido encontrado'}), 400
        
        total_blocks = len(zpl_blocks)
        print(f"📊 TOTAL DE BLOCOS: {total_blocks}")
        print(f"📦 PROCESSANDO PARTE: {start_block}-{end_block}")
        
        # Validar range
        if start_block < 1 or end_block > total_blocks or start_block > end_block:
            return jsonify({'error': f'Range inválido. Blocos disponíveis: 1-{total_blocks}'}), 400
        
        # Extrair blocos da parte selecionada (índices baseados em 0)
        selected_blocks = zpl_blocks[start_block-1:end_block]
        print(f"📋 BLOCOS SELECIONADOS: {len(selected_blocks)}")
        
        # Processar blocos selecionados
        return process_selected_blocks(selected_blocks, start_block, end_block)
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_selected_blocks(zpl_blocks, start_num, end_num):
    """Processa apenas os blocos selecionados"""
    try:
        pdf_merger = PdfMerger()
        temp_files = []
        
        # Lotes de 5 blocos para estabilidade
        batch_size = 5
        total_batches = (len(zpl_blocks) + batch_size - 1) // batch_size
        
        print(f"🔄 Processando {len(zpl_blocks)} blocos em {total_batches} lotes de {batch_size}")
        
        for i in range(0, len(zpl_blocks), batch_size):
            batch = zpl_blocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            print(f"📦 Lote {batch_num}/{total_batches} ({len(batch)} blocos)")
            
            # Tentar processar lote
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
                        print(f"✅ Lote {batch_num} processado ({len(response.content)} bytes)")
                        success = True
                        break
                    else:
                        print(f"❌ Tentativa {attempt + 1}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Tentativa {attempt + 1}: {str(e)}")
                
                if attempt < 2:
                    time.sleep(1)
            
            if not success:
                print(f"💥 Lote {batch_num} falhou após 3 tentativas")
            
            # Pausa pequena entre lotes
            time.sleep(0.5)
        
        if not temp_files:
            return jsonify({'error': 'Nenhum lote processado com sucesso'}), 500
        
        # Criar PDF final da parte
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
                import os
                os.unlink(temp_file)
            except:
                pass
        
        file_size_kb = len(output_buffer.getvalue()) / 1024
        print(f"✅ PDF PARTE {start_num}-{end_num}: {len(zpl_blocks)} blocos, {file_size_kb:.1f}KB")
        
        return send_file(final_temp.name, as_attachment=True, download_name=f'etiquetas_parte_{start_num}-{end_num}.pdf')
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
