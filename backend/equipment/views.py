import os
import pandas as pd
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from reportlab.pdfgen import canvas

from .models import Dataset


@api_view(['POST'])
def upload_csv(request):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided.'}, status=400)

    # Save uploaded file to model
    ds = Dataset(filename=file.name)
    ds.file.save(file.name, file)

    # Read CSV from saved file path (robust for large files)
    df = pd.read_csv(ds.file.path)

    # Compute summary statistics
    result = {
        "total_rows": int(len(df)),
        "average_pressure": float(round(df['Pressure'].mean(), 2)) if 'Pressure' in df.columns else None,
        "average_temperature": float(round(df['Temperature'].mean(), 2)) if 'Temperature' in df.columns else None,
        "type_distribution": df['Type'].value_counts().to_dict() if 'Type' in df.columns else {}
    }

    # Save summary on the Dataset record
    ds.summary = result
    ds.save()

    # Generate PDF report saved under media/reports/
    report_path = generate_pdf(result, ds.id)

    # store relative report path on model and save
    ds.report = report_path
    ds.save()

    # build absolute URL for frontend consumption
    try:
        report_url = request.build_absolute_uri(report_path)
    except Exception:
        report_url = report_path

    return Response({
        "message": "CSV uploaded successfully. PDF report generated.",
        "data": result,
        "report": report_url,
        "dataset_id": ds.id
    })


def generate_pdf(data, dataset_id=None):
    reports_dir = os.path.join(settings.BASE_DIR, 'media', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{dataset_id or 'latest'}.pdf"
    path = os.path.join(reports_dir, filename)

    c = canvas.Canvas(path)
    y = 800
    c.setFont('Helvetica-Bold', 14)
    c.drawString(50, y, "Chemical Equipment Data Report")
    y -= 40

    c.setFont('Helvetica', 11)
    for key, value in data.items():
        c.drawString(50, y, f"{key}: {value}")
        y -= 22
        if y < 80:
            c.showPage()
            y = 800

    c.save()

    # Return relative media path for frontend consumption
    return f"{settings.MEDIA_URL}reports/{filename}"


@api_view(['GET'])
def datasets_list(request):
    # support pagination via ?page=1&page_size=5
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 5))
    except ValueError:
        page = 1
        page_size = 5

    qs_all = Dataset.objects.order_by('-uploaded_at')
    total = qs_all.count()
    start = (page - 1) * page_size
    end = start + page_size
    qs = qs_all[start:end]

    items = []
    for d in qs:
        report_url = d.report
        try:
            report_url = request.build_absolute_uri(report_url) if report_url else None
        except Exception:
            pass

        items.append({
            'id': d.id,
            'filename': d.filename,
            'uploaded_at': d.uploaded_at,
            'summary': d.summary,
            'report_url': report_url,
        })

    return Response({
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
    })



@api_view(['GET'])
def dataset_preview(request, pk):
    # Return first 10 rows of original CSV as JSON for preview
    try:
        ds = Dataset.objects.get(pk=pk)
    except Dataset.DoesNotExist:
        return Response({'error': 'Dataset not found.'}, status=404)

    if not ds.file:
        return Response({'error': 'No file available for this dataset.'}, status=400)

    try:
        df = pd.read_csv(ds.file.path, nrows=10)
        preview = {
            'columns': list(df.columns),
            'rows': df.fillna('').to_dict(orient='records')
        }
        return Response(preview)
    except Exception as e:
        return Response({'error': f'Could not read CSV: {e}'}, status=500)

