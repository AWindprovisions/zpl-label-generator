from flask import Flask, request, jsonify, send_file
import requests
import tempfile
import os

app = Flask(__name__)

# HTML embutido diretamente na rota
@app.route('/')
def index():
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZPL Generator - Ultra Simples</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .logo { font-size: 48px; }
        textarea { width: 100%; height: 200px; padding: 10px; font-family: monospace; }
        button { width: 100%; padding: 15px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🏷️</div>
        <h1>ZPL Generator</h1>
        <p>Ultra Simples - 8cm × 2,5cm</p>
    </div>
    
    <form id="zplForm">
        <label for="zplCode">Cole seu código ZPL:</label><br><br>
        <textarea id="zplCode" placeholder="^XA^CI28
^LH0,0
^FO30,15^BY2,,0^BCN,54,N,N^FDTEST123^FS
^FO105,75^A0N,20,25^FH^FDTEST123^FS
^XZ"></textarea><br><br>
        <button type="submit">🚀 Gerar PDF</button>
    </form>
    
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
            
            button.disabled = true;
            button.textContent = '⏳ Processando...';
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
                    a.download = 'etiquetas.pdf';
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    result.innerHTML = '<div class="result success">✅ PDF gerado e baixado!</div>';
                } else {
                    const error = await response.json();
                    result.innerHTML = `<div class="result error">❌ ${error.error}</div>`;
                }
            } catch (error) {
                result.innerHTML = `<div class="result error">❌ Erro: ${error.message}</div>`;
            } finally {
                button.disabled = false;
                button.textContent = '🚀 Gerar PDF';
            }
        });
    </script>
</body>
</html>'''

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        zpl_code = data.get('zpl', '').strip()
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL vazio'}), 400
        
        # Garantir formato correto
        if not zpl_code.startswith('^XA'):
            zpl_code = '^XA\n' + zpl_code
        if not zpl_code.endswith('^XZ'):
            zpl_code = zpl_code + '\n^XZ'
        
        # Chamar Labelary diretamente
        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/3.15x0.98/0/'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/pdf'
        }
        
        response = requests.post(url, data=zpl_code, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Salvar em arquivo temporário
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            return send_file(temp_file.name, as_attachment=True, download_name='etiquetas.pdf')
        else:
            return jsonify({'error': f'Erro Labelary: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
