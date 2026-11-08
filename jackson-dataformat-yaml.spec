Name:		jackson-dataformat-yaml
Version:	2.23.0
Release:	1
Summary:	YAML backend for Jackson
Group:		Development/Java
License:	ASL 2.0
URL:		https://github.com/FasterXML/jackson-dataformats-text
Source0:	https://github.com/FasterXML/jackson-dataformats-text/archive/refs/tags/jackson-dataformats-text-%{version}.tar.gz#/jackson-dataformats-text-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	python
# databind's published POM parents are not Requires of that RPM.
BuildRequires:	mvn(com.fasterxml.jackson:jackson-base:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-bom:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-parent:pom::)
BuildRequires:	mvn(com.fasterxml:oss-parent:pom::)
BuildRequires:	mvn(com.fasterxml.jackson.core:jackson-databind)
BuildRequires:	jackson-databind >= 2.23.0
BuildRequires:	jackson-core >= 2.23.0
BuildRequires:	jackson-annotations >= 2.23
BuildRequires:	jackson-bom >= 2.23.0
BuildRequires:	jackson-parent >= 2.23
BuildRequires:	fasterxml-oss-parent >= 81
BuildRequires:	mvn(org.yaml:snakeyaml)
BuildRequires:	snakeyaml >= 2.7-2
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven

Obsoletes:	%{name}-javadoc < %{version}

%description
Reads and writes YAML through Jackson. 2.23.0 matches databind
2.23.0 and uses the system SnakeYAML jar. It rejects invalid
UTF-8, limits document length, quotes YAML 1.1 number forms when
asked to quote numbers as strings, and constrains nested merge
keys. The Java module is
com.fasterxml.jackson.dataformat.yaml. Tests are skipped.

%prep
%autosetup -n jackson-dataformats-text-jackson-dataformats-text-%{version}
# The text parent is not published. Keep only the YAML module, and
# give databind an explicit version so the flattened POM resolves.
python - <<'PY'
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://maven.apache.org/POM/4.0.0"
ET.register_namespace("", NS)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

def local(tag):
    return tag.rsplit("}", 1)[-1]

def artifact_of(elem):
    for item in elem:
        if local(item.tag) == "artifactId":
            return (item.text or "").strip()
    return ""

def child_text(elem, name):
    for item in elem:
        if local(item.tag) == name:
            return (item.text or "").strip()
    return ""

drop = {
    "replacer",
    "cyclonedx-maven-plugin",
    "moditect-maven-plugin",
    "gradle-module-metadata-maven-plugin",
}
path = Path("yaml/pom.xml")
tree = ET.parse(path)
root = tree.getroot()
removed = []
tag = "{" + NS + "}"
for child in list(root):
    if local(child.tag) == "parent":
        root.remove(child)
        removed.append("parent")
for parent in list(root.iter()):
    for child in list(parent):
        if local(child.tag) == "plugin" and artifact_of(child) in drop:
            parent.remove(child)
            removed.append(artifact_of(child))
missing = drop - set(removed)
if missing or "parent" not in removed:
    raise SystemExit("not removed " + " ".join(sorted(missing)))
# groupId and version were inherited.
group = ET.Element(tag + "groupId")
group.text = "com.fasterxml.jackson.dataformat"
version = ET.Element(tag + "version")
version.text = "%{version}"
artifact = None
for child in list(root):
    if local(child.tag) == "artifactId":
        artifact = child
if artifact is None:
    raise SystemExit("artifactId missing")
index = list(root).index(artifact)
root.insert(index, group)
root.insert(index + 2, version)
found = {"jackson-databind": False, "snakeyaml": False}
for dep in root.iter():
    if local(dep.tag) != "dependency":
        continue
    name = artifact_of(dep)
    if name not in found:
        continue
    found[name] = True
    if name == "jackson-databind" and not child_text(dep, "version"):
        ver = ET.Element(tag + "version")
        ver.text = "%{version}"
        dep.append(ver)
if not all(found.values()):
    raise SystemExit("dependency missing " + str(found))
# The text parent is gone, so the compiler no longer inherits 1.8.
props = None
for child in list(root):
    if local(child.tag) == "properties":
        props = child
if props is None:
    props = ET.Element(tag + "properties")
    root.append(props)
for name, value in (
    ("maven.compiler.source", "1.8"),
    ("maven.compiler.target", "1.8"),
):
    node = ET.Element(tag + name)
    node.text = value
    props.append(node)
plugins = None
for child in root:
    if local(child.tag) != "build":
        continue
    for item in child:
        if local(item.tag) == "plugins":
            plugins = item
if plugins is None:
    raise SystemExit("plugins missing")
jar = ET.Element(tag + "plugin")
jgroup = ET.SubElement(jar, tag + "groupId")
jgroup.text = "org.apache.maven.plugins"
jartifact = ET.SubElement(jar, tag + "artifactId")
jartifact.text = "maven-jar-plugin"
jversion = ET.SubElement(jar, tag + "version")
jversion.text = "3.5.1"
conf = ET.SubElement(jar, tag + "configuration")
archive = ET.SubElement(conf, tag + "archive")
entries = ET.SubElement(archive, tag + "manifestEntries")
flag = ET.SubElement(entries, tag + "Multi-Release")
flag.text = "true"
plugins.insert(0, jar)
tree.write(Path("pom.xml"), encoding="UTF-8", xml_declaration=True)
text = Path("pom.xml").read_text(encoding="utf-8")
if "<artifactId>jackson-dataformats-text</artifactId>" in text or "moditect-maven-plugin" in text:
    raise SystemExit("parent or moditect survived")

src = Path("yaml/src/main/java/com/fasterxml/jackson/dataformat/yaml/PackageVersion.java.in")
body = src.read_text(encoding="utf-8")
body = body.replace("@package@", "com.fasterxml.jackson.dataformat.yaml")
body = body.replace("@projectversion@", "%{version}")
body = body.replace("@projectgroupid@", "com.fasterxml.jackson.dataformat")
body = body.replace("@projectartifactid@", "jackson-dataformat-yaml")
for token in ("@package@", "@projectversion@", "@projectgroupid@", "@projectartifactid@"):
    if token in body:
        raise SystemExit("placeholder left")
src.with_suffix("").write_text(body, encoding="utf-8")
src.unlink()
shutil.move("yaml/src", "src")
for name in ("csv", "properties", "toml", "yaml"):
    shutil.rmtree(name)
PY

%build -a
mkdir -p target/classes/META-INF/versions/9
javac --release 9 \
	--module-path /usr/share/java/jackson-core.jar:/usr/share/java/jackson-databind.jar:/usr/share/java/jackson-annotations.jar:/usr/share/java/snakeyaml.jar \
	--patch-module com.fasterxml.jackson.dataformat.yaml=target/classes \
	-d target/classes/META-INF/versions/9 \
	src/moditect/module-info.java
test -s target/classes/META-INF/versions/9/module-info.class
jar uf target/jackson-dataformat-yaml-%{version}.jar -C target/classes META-INF/versions/9/module-info.class
java --module-path target/jackson-dataformat-yaml-%{version}.jar:/usr/share/java/jackson-core.jar:/usr/share/java/jackson-databind.jar:/usr/share/java/jackson-annotations.jar:/usr/share/java/snakeyaml.jar --describe-module com.fasterxml.jackson.dataformat.yaml | grep -q '^com.fasterxml.jackson.dataformat.yaml'

%files -f .mfiles
%doc LICENSE README.md SECURITY.md release-notes/VERSION-2.x
