import re
import time
import requests
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from PyPDF2 import PdfMerger
from .auth import require_auth

zpl_bp = Blueprint('zpl', __name__)

@zpl_bp.route('/process-zpl', methods=['POST'])
@require_auth
def process_zpl(current_user):
    try:
        data = request.get_json()
        zpl_code = data.get('zpl_code', '')
        width = data.get('width', 8)  # cm
        height = data.get('height', 2.5)  # cm
        add_separators = data.get('add_separators', True)
        
        print(f"DEBUG: Usuário {current_user} - Recebido ZPL com {len(zpl_code)} caracteres")
        print(f"DEBUG: Dimensões: {width}x{height}cm")
        
        if not zpl_code:
            return jsonify({'error': 'Código ZPL é obrigatório'}), 400
        
        # Extrair etiquetas individuais
        labels = extract_zpl_labels(zpl_code)
        print(f"DEBUG: Extraídas {len(labels)} etiquetas")
        
        if not labels:
            return jsonify({'error': 'Nenhuma etiqueta ZPL válida encontrada'}), 400
        
        # Adicionar separadores se solicitado
        if add_separators:
            labels = add_sku_separators(labels)
            print(f"DEBUG: Após separadores: {len(labels)} etiquetas")
        
        # Processar em lotes de 50
        batch_size = 50
        pdf_files = []
        
        for i in range(0, len(labels), batch_size):
            batch = labels[i:i + batch_size]
            batch_zpl = '\n'.join(batch)
            
            print(f"DEBUG: Processando lote {i//batch_size + 1} com {len(batch)} etiquetas")
            
            # Chamar API do Labelary
            pdf_content = call_labelary_api(batch_zpl, width, height)
            if pdf_content:
                print(f"DEBUG: Lote {i//batch_size + 1} gerou PDF de {len(pdf_content)} bytes")
                pdf_files.append(pdf_content)
            else:
                print(f"DEBUG: Lote {i//batch_size + 1} falhou")
            
            # Delay para evitar rate limiting
            time.sleep(0.5)
        
        print(f"DEBUG: Total de PDFs gerados: {len(pdf_files)}")
        
        # Unir todos os PDFs
        if pdf_files:
            merged_pdf = merge_pdfs(pdf_files)
            print(f"DEBUG: PDF final tem {len(merged_pdf)} bytes")
            return send_file(
                BytesIO(merged_pdf),
                as_attachment=True,
                download_name='etiquetas.pdf',
                mimetype='application/pdf'
            )
        else:
            return jsonify({'error': 'Falha ao gerar PDFs'}), 500
            
    except Exception as e:
        print(f"DEBUG: Erro: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

def extract_zpl_labels(zpl_code):
    """Extrai etiquetas individuais do código ZPL"""
    # Limpar o código ZPL
    zpl_code = zpl_code.strip()
    
    # Se o código não começar com ^XA, adicionar
    if not zpl_code.startswith('^XA'):
        zpl_code = '^XA\n' + zpl_code
    
    # Se o código não terminar com ^XZ, adicionar
    if not zpl_code.endswith('^XZ'):
        zpl_code = zpl_code + '\n^XZ'
    
    print(f"DEBUG: ZPL após correção: {zpl_code[:200]}...")
    
    # Dividir por ^XA (início de etiqueta)
    parts = zpl_code.split('^XA')
    labels = []
    
    for part in parts:
        if part.strip():
            # Adicionar ^XA de volta e garantir que termine com ^XZ
            label = '^XA' + part.strip()
            if not label.endswith('^XZ'):
                label += '\n^XZ'
            labels.append(label)
    
    print(f"DEBUG: Etiquetas extraídas: {len(labels)}")
    for i, label in enumerate(labels[:3]):  # Mostrar apenas as 3 primeiras
        print(f"DEBUG: Etiqueta {i+1}: {label[:100]}...")
    
    return labels

def extract_sku_from_label(label):
    """Extrai o SKU de uma etiqueta ZPL"""
    # Procurar por padrões de SKU (letras e números)
    match = re.search(r'\^FD([A-Z0-9]{5,})\^FS', label)
    if match:
        return match.group(1)
    return None

def add_sku_separators(labels):
    """Adiciona etiquetas de separação entre SKUs diferentes"""
    if not labels:
        return labels
    
    result = []
    current_sku = None
    
    for label in labels:
        sku = extract_sku_from_label(label)
        
        # Se mudou o SKU, adicionar separador
        if current_sku and sku and current_sku != sku:
            separator_zpl = create_separator_label()
            result.append(separator_zpl)
        
        result.append(label)
        if sku:
            current_sku = sku
    
    return result

def create_separator_label():
    """Cria uma etiqueta de separação com a letra 'E'"""
    return """^XA
^FO100,50^A0N,50,50^FDE^FS
^XZ"""

def call_labelary_api(zpl_code, width, height):
    """Chama a API do Labelary para converter ZPL em PDF"""
    try:
        # Converter cm para polegadas
        width_inches = width / 2.54
        height_inches = height / 2.54
        
        url = f"http://api.labelary.com/v1/printers/8dpmm/labels/{width_inches:.1f}x{height_inches:.1f}/"
        
        print(f"DEBUG: Chamando Labelary URL: {url}")
        print(f"DEBUG: ZPL enviado ({len(zpl_code)} chars): {zpl_code[:200]}...")
        
        response = requests.post(
            url,
            data=zpl_code.encode('utf-8'),
            headers={'Accept': 'application/pdf'},
            timeout=30
        )
        
        print(f"DEBUG: Resposta Labelary: {response.status_code}")
        print(f"DEBUG: Headers resposta: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"DEBUG: PDF recebido com {len(response.content)} bytes")
            return response.content
        else:
            print(f"DEBUG: Erro da API Labelary: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"DEBUG: Erro ao chamar API Labelary: {e}")
        return None

def merge_pdfs(pdf_files):
    """Une múltiplos PDFs em um único arquivo"""
    merger = PdfMerger()
    
    for pdf_content in pdf_files:
        merger.append(BytesIO(pdf_content))
    
    output = BytesIO()
    merger.write(output)
    merger.close()
    
    return output.getvalue()

