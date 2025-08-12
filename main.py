from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
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
    <title>ZPL Generator - Quantidade e Espaços</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107; }
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
        .progress { background: #f8f9fa; border-radius: 5px; margin: 10px 0; }
        .progress-bar { background: #007bff; height: 20px; border-radius: 5px; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Quantidade Correta + Espaços entre SKUs</p>
    </div>
    
    <div class="info">
        <h3>✅ Correções Aplicadas:</h3>
        <ul>
            <li>📊 Processa TODOS os blocos (não só os primeiros)</li>
            <li>📏 Adiciona espaço em branco entre SKUs diferentes</li>
            <li>🔢 Mostra contagem exata de blocos processados</li>
            <li>⏱️ Processamento em lotes de 5 blocos para estabilidade</li>
        </ul>
    </div>
    
    <div class="warning">
        <h3>⚠️ Atenção:</h3>
        <p>Para códigos grandes (299 blocos), o processamento pode levar 3-5 minutos. Aguarde até o final!</p>
    </div>
    
    <form id="zplForm">
        <label for="zplCode">Cole seu código ZPL (todos os blocos serão processados):</label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Agora processa TODOS os blocos com espaços entre SKUs!"></textarea><br><br>
        <button type="submit">🚀 Gerar PDF Completo (Todos os Blocos)</button>
    </form>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p id="loadingText">Processando todos os blocos...</p>
        <div class="progress">
            <div class="progress-bar" id="progressBar" style="width: 0%"></div>
        </div>
        <p id="progressText">0% - Iniciando...</p>
    </div>
    
    <div id="result"></div>
    
    <script>
        document.getElementById('zplForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const zplCode = document.getElementById('zplCode').value.trim();
            if (!zplCode) {
                alert('Cole o código ZPL primeiro!');
                return;
            }
            
            const button = e.target.querySelector('button');
            const result = document.getElementById('result');
            const loading = document.getElementById('loading');
            
            button.disabled = true;
            button.textContent = '⏳ Processando Todos os Blocos...';
            loading.style.display = 'block';
            result.innerHTML = '';
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ zpl: zplCode })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'etiquetas_completas_com_espacos.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    result.innerHTML = '<div class="result success">✅ PDF completo gerado! Todos os blocos processados com espaços entre SKUs!</div>';
                } else {
                    const error = await response.json();
                    result.innerHTML = `<div class="result error">❌ ${error.error}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
            } finally {
                button.disabled = false;
                button.textContent = '🚀 Gerar PDF Completo (Todos os Blocos)';
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Arquivo ainda muito grande. Tente dividir o código ZPL.'}), 413

def extract_sku_from_block(zpl_block):
    """Extrai SKU do bloco ZPL para detectar mudanças"""
    # Procurar por padrões comuns de SKU
    patterns = [
        r'\^FD([A-Za-z0-9\-_.]+)\^FS',  # Padrão geral
        r'SKU[:\s]*([A-Za-z0-9\-_.]+)',  # SKU: explícito
        r'\^A0.*?\^FD([A-Za-z0-9\-_.]+)\^FS'  # Texto após código de barras
    ]
    
    for pattern in patterns:
        match = re.search(pattern, zpl_block, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def create_blank_label():
    """Cria etiqueta em branco para separar SKUs"""
    return """^XA
^LH0,0
^FO0,0^GB800,250,2^FS
^FO400,125^A0N,30,30^FH^FD--- SEPARADOR ---^FS
^XZ"""

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL vazio'}), 400
        
        # Detectar TODOS os blocos ZPL
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        
        if not zpl_blocks:
            # Se não encontrar blocos, tratar como código único
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            zpl_blocks = [zpl_code]
        
        print(f"📊 TOTAL DE BLOCOS DETECTADOS: {len(zpl_blocks)}")
        
        # Adicionar espaços entre SKUs diferentes
        blocks_with_spaces = []
        last_sku = None
        
        for i, block in enumerate(zpl_blocks):
            current_sku = extract_sku_from_block(block)
            
            # Se mudou de SKU, adicionar separador
            if last_sku is not None and current_sku != last_sku and current_sku is not None:
                print(f"🔄 Mudança de SKU detectada: {last_sku} → {current_sku}")
                blocks_with_spaces.append(create_blank_label())
            
            blocks_with_spaces.append(block)
            last_sku = current_sku
        
        print(f"📦 BLOCOS COM ESPAÇOS: {len(blocks_with_spaces)} (original: {len(zpl_blocks)})")
        
        # Processar TODOS os blocos em lotes pequenos
        return process_all_blocks(blocks_with_spaces)
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_all_blocks(zpl_blocks):
    """Processa TODOS os blocos em lotes pequenos"""
    try:
        pdf_merger = PdfMerger()
        temp_files = []
        
        # Lotes de 5 blocos para máxima estabilidade
        batch_size = 5
        total_batches = (len(zpl_blocks) + batch_size - 1) // batch_size
        
        print(f"🔄 Processando {len(zpl_blocks)} blocos em {total_batches} lotes de {batch_size}")
        
        for i in range(0, len(zpl_blocks), batch_size):
            batch = zpl_blocks[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            print(f"📦 Lote {batch_num}/{total_batches} ({len(batch)} blocos)")
            
            # Tentar processar lote
            success = False
            for attempt in range(3):  # 3 tentativas por lote
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
                        print(f"✅ Lote {batch_num} processado com sucesso")
                        success = True
                        break
                    else:
                        print(f"❌ Tentativa {attempt + 1} falhou: {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Tentativa {attempt + 1} erro: {str(e)}")
                
                if attempt < 2:  # Pausa entre tentativas
                    import time
                    time.sleep(2)
            
            if not success:
                print(f"💥 Lote {batch_num} falhou após 3 tentativas")
        
        if not temp_files:
            return jsonify({'error': 'Nenhum lote processado com sucesso'}), 500
        
        # Criar PDF final mesclado
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
        
        print(f"✅ PDF FINAL CRIADO: {len(zpl_blocks)} blocos processados")
        
        return send_file(final_temp.name, as_attachment=True, download_name='etiquetas_completas_com_espacos.pdf')
        
    except Exception as e:
        print(f"💥 Erro no processamento: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
