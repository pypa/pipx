{% if render_title %}
.. _release-{{ versiondata.version|replace('.', '-') }}:

{% if versiondata.name %}
{{ versiondata.name }} {{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.name + versiondata.version + versiondata.date)|length + 4)}}
{% else %}
{{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.version + versiondata.date)|length + 3)}}
{% endif %}
{% endif %}
{% for section, _ in sections.items() %}
{% set underline = underlines[0] %}{% if section %}{{section}}
{{ underline * section|length }}{% set underline = underlines[1] %}

{% endif %}

{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section]%}
.. _release-{{ versiondata.version|replace('.', '-') }}-{{ definitions[category]['name']|lower|replace(' ', '-') }}:

{{ definitions[category]['name'] }}
{{ underline * definitions[category]['name']|length }}

{% for text, values in sections[section][category].items() %}
{% set visible_values = values|reject('in', text|replace(':pr:', ':issue:'))|list %}
- {% if text %}{{ text }}{% if visible_values %} ({{ visible_values|join(', ') }}){% endif %}{% else %}{{ visible_values|join(', ') }}{% endif  %}

{% endfor %}

{% if sections[section][category]|length == 0 %}
No significant changes.

{% else %}
{% endif %}

{% endfor %}
{% else %}
No significant changes.


{% endif %}
{% endfor %}
