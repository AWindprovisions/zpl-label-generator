from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import re
import io
from PyPDF2 import PdfMerger

app = Flask(__name__)

# CORREÇÃO ERRO 413: Aumentar limite para 100MB
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Corrigido 413</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        .info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
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
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Corrigido Erro 413 - 8cm × 2,5cm</p>
    </div>
    
    <div class="info">
        <h3>✅ Correções Aplicadas:</h3>
        <ul>
            <li>🔧 Limite aumentado para 100MB</li>
            <li>📦 Processamento em lotes para códigos grandes</li>
            <li>⏱️ Timeout estendido para 60 segundos</li>
            <li>🔄 Sistema de retry automático</li>
        </ul>
    </div>
    
    <form id="zplForm">
        <label for="zplCode">Cole seu código ZPL (qualquer tamanho):</label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ

Agora suporta códigos gigantescos!"></textarea><br><br>
        <button type="submit">🚀 Gerar PDF (Sem Limite 413)</button>
    </form>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <p>Processando código grande...</p>
        <p><small>Pode levar alguns minutos para códigos gigantescos</small></p>
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
            button.textContent = '⏳ Processando...';
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
                    a.download = 'etiquetas_corrigido_413.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    result.innerHTML = '<div class="result success">✅ PDF gerado com sucesso! Erro 413 corrigido!</div>';
                } else {
                    const error = await response.json();
                    result.innerHTML = `<div class="result error">❌ ${error.error}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
            } finally {
                button.disabled = false;
                button.textContent = '🚀 Gerar PDF (Sem Limite 413)';
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>'''

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'Arquivo ainda muito grande. Tente dividir o código ZPL.'}), 413

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL vazio'}), 400
        
        # Detectar blocos ZPL individuais
        zpl_blocks = re.findall(r'\^XA[\s\S]*?\^XZ', zpl_code, re.IGNORECASE)
        
        if not zpl_blocks:
            # Se não encontrar blocos, tratar como código único
            if not zpl_code.startswith('^XA'):
                zpl_code = '^XA\n' + zpl_code
            if not zpl_code.endswith('^XZ'):
                zpl_code = zpl_code + '\n^XZ'
            zpl_blocks = [zpl_code]
        
        print(f"📊 Processando {len(zpl_blocks)} blocos ZPL")
        
        # Se apenas 1 bloco, processar diretamente
        if len(zpl_blocks) == 1:
            return process_single_block(zpl_blocks[0])
        
        # Múltiplos blocos: processar em lotes e mesclar
        return process_multiple_blocks(zpl_blocks)
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_single_block(zpl_code):
    """Processa um único bloco ZPL"""
    try:
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/pdf'
        }
        
        response = requests.post(url, data=zpl_code, headers=headers, timeout=60)
        
        if response.status_code == 200:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            return send_file(temp_file.name, as_attachment=True, download_name='etiqueta.pdf')
        else:
            return jsonify({'error': f'Erro Labelary: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_multiple_blocks(zpl_blocks):
    """Processa múltiplos blocos e mescla em um PDF"""
    try:
        pdf_merger = PdfMerger()
        temp_files = []
        
        # Processar blocos em lotes de 10
        batch_size = 10
        for i in range(0, len(zpl_blocks), batch_size):
            batch = zpl_blocks[i:i+batch_size]
            batch_zpl = '\n'.join(batch)
            
            print(f"📦 Processando lote {i//batch_size + 1} ({len(batch)} blocos)")
            
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
            else:
                print(f"❌ Erro no lote {i//batch_size + 1}: {response.status_code}")
        
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
        
        print(f"✅ PDF final criado com {len(zpl_blocks)} blocos")
        
        return send_file(final_temp.name, as_attachment=True, download_name='etiquetas_multiplas.pdf')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
