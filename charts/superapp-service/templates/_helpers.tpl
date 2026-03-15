{{/*
Expand the name of the chart.
*/}}
{{- define "superapp-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "superapp-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Selector labels */}}
{{- define "superapp-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "superapp-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Common labels */}}
{{- define "superapp-service.labels" -}}
helm.sh/chart: {{ include "superapp-service.name" . }}
{{ include "superapp-service.selectorLabels" . }}
{{- end }}

{{/* ServiceAccount */}}
{{- define "superapp-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "superapp-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
