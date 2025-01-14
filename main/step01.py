import os, json, sys
from fontTools.ttLib import TTFont

pydir=os.path.abspath(os.path.dirname(__file__))
cfg=json.load(open(os.path.join(pydir, 'configs/config.json'), 'r', encoding='utf-8'))

def setcg(code, glyf):
	for table in font["cmap"].tables:
		if (table.format==4 and code<=0xFFFF) or table.format==12 or code in table.cmap:
			table.cmap[code]=glyf
def glfrtxt(txt):
	cmap=font.getBestCmap()
	glys=list()
	for ch in txt:
		if ord(ch) in cmap and cmap[ord(ch)] not in glys:
			glys.append(cmap[ord(ch)])
	return glys
def glyrepl(repdic):
	for table in font["cmap"].tables:
		for cd in table.cmap:
			if table.cmap[cd] in repdic:
				table.cmap[cd]=repdic[table.cmap[cd]]
				print('Remapping', chr(cd))
def locllki(ftgsub, lan):
	ftl, lkl=list(), list()
	for sr in ftgsub.table.ScriptList.ScriptRecord:
		for lsr in sr.Script.LangSysRecord:
			if lsr.LangSysTag.strip()==lan:
				ftl+=lsr.LangSys.FeatureIndex
	for ki in ftl:
		ftg=ftgsub.table.FeatureList.FeatureRecord[ki].FeatureTag
		if ftg=='locl':
			lkl+=ftgsub.table.FeatureList.FeatureRecord[ki].Feature.LookupListIndex
	return list(dict.fromkeys(lkl))
def getloclk(ckfont, lan):
	locdics=list()
	for lki in locllki(ckfont["GSUB"], lan):
		locrpl=dict()
		for st in ckfont["GSUB"].table.LookupList.Lookup[lki].SubTable:
			if st.LookupType==7 and st.ExtSubTable.LookupType==1:
				tabl=st.ExtSubTable.mapping
			elif st.LookupType==1:
				tabl=st.mapping
			for g1 in tabl:
				locrpl[g1]=tabl[g1]
		locdics.append(locrpl)
	return locdics
def glfrloc(gl, loclk):
	for dc in loclk:
		if gl in dc: return dc[gl]

def locglrpl():
	locgls=dict()
	shset=json.load(open(os.path.join(pydir, 'configs/sourcehan.json'), 'r', encoding='utf-8'))
	if ssty in ('Sans', 'Mono'): shset['hcgl']+=shset['hcglsans']
	krgl, scgl, tcgl, hcgl=glfrtxt(shset['krgl']), glfrtxt(shset['scgl']), glfrtxt(shset['tcgl']), glfrtxt(shset['hcgl'])
	for glloc in ((krgl, lockor), (scgl, loczhs), (tcgl, loczht), (hcgl, loczhh)):
		for g1 in glloc[0]:
			assert g1 not in locgls, g1
			g2=glfrloc(g1, glloc[1])
			if g2: locgls[g1]=g2
	return locgls
def uvstab():
	cmap=font.getBestCmap()
	uvsdc, allgls=dict(), set()
	for table in font["cmap"].tables:
		if table.format==14:
			for vsl in table.uvsDict.keys():
				newl=list()
				for cg in table.uvsDict[vsl]:
					if cg[0] not in uvsdc:
						uvsdc[cg[0]]=dict()
					if cg[1]==None:
						newl.append((cg[0], cmap[cg[0]]))
						uvsdc[cg[0]][vsl]=cmap[cg[0]]
						allgls.add(cmap[cg[0]])
					else:
						newl.append((cg[0], cg[1]))
						uvsdc[cg[0]][vsl]=cg[1]
						allgls.add(cg[1])
				table.uvsDict[vsl]=newl
			glgcn=glfrloc(cmap[ord('关')], loczhs)
			if glgcn and (ord('关'), glgcn) not in table.uvsDict[0xE0101]:
				table.uvsDict[0xE0101].append((ord('关'), glgcn))
				allgls.add(glgcn)
	return uvsdc, allgls
def ftuvstab():
	cmap=font.getBestCmap()
	for table in font["cmap"].tables:
		if table.format==14:
			for vsl in table.uvsDict.keys():
				newl=list()
				for cg in table.uvsDict[vsl]:
					if cg[1]==cmap[cg[0]]:
						newl.append((cg[0], None))
					else:
						newl.append((cg[0], cg[1]))
				table.uvsDict[vsl]=newl
def getuvs(fonto, fcmap):
	nuv=dict()
	for table in fonto["cmap"].tables:
		if table.format==14:
			for vsl in table.uvsDict.keys():
				for cg in table.uvsDict[vsl]:
					if cg[0] not in nuv:
						nuv[cg[0]]=dict()
					if cg[1]==None:
						nuv[cg[0]][vsl]=fcmap[cg[0]]
					else:
						nuv[cg[0]][vsl]=cg[1]
	return nuv
def setuvs():
	uvcfg=json.load(open(os.path.join(pydir, 'configs/uvs.json'), 'r', encoding='utf-8'))
	tv=dict()
	for ch in uvcfg.keys():
		tv[ord(ch)]=int(uvcfg[ch], 16)
	for k in uvdic.keys():
		if k in tv and tv[k] in uvdic[k]:
			print('Remapping uvs', chr(k))
			setcg(k, uvdic[k][tv[k]])
def getother(font2, repdict):
	print('Processing...')
	if 'CFF ' in font or 'CFF2' in font:
		if 'CFF2' in font:
			cff=font['CFF2'].cff
			cff2=font2['CFF2'].cff
		else:
			cff=font['CFF '].cff
			cff2=font2['CFF '].cff
		cff2.desubroutinize()
		for fontname in cff.keys():
			fontsub=cff[fontname]
			cs=fontsub.CharStrings
			for fontname2 in cff2.keys():
				fontsub2=cff2[fontname2]
				cs2=fontsub2.CharStrings
				for gl in repdict.keys():
					cs[gl]=cs2[repdict[gl]]
					font['hmtx'][gl]=font2['hmtx'][repdict[gl]]
					font['vmtx'][gl]=font2['vmtx'][repdict[gl]]
					if 'VORG' in font and 'VORG' in font2:
						if repdict[gl] in set(font2['VORG'].VOriginRecords.keys()):
							font['VORG'].VOriginRecords[gl]=font2['VORG'].VOriginRecords[repdict[gl]]
						elif gl in set(font['VORG'].VOriginRecords.keys()):
							del font['VORG'].VOriginRecords[gl]
	elif 'glyf' in font:
		for gl in repdict.keys():
			font['glyf'].glyphs[gl]=font2['glyf'].glyphs[repdict[gl]]
			font['hmtx'][gl]=font2['hmtx'][repdict[gl]]
			font['vmtx'][gl]=font2['vmtx'][repdict[gl]]
			font['gvar'].variations[gl]=font2['gvar'].variations[repdict[gl]]
			if 'VORG' in font:
				font['VORG'].VOriginRecords[gl]=font2['VORG'].VOriginRecords[repdict[gl]]
	else:
		raise
def subcff(cfftb, glyphs):
	ftcff=cfftb.cff
	for fontname in ftcff.keys():
		fontsub=ftcff[fontname]
		cs=fontsub.CharStrings
		for g in fontsub.charset:
			if g not in glyphs: continue
			c, _=cs.getItemAndSelector(g)
		if cs.charStringsAreIndexed:
			indices=[i for i,g in enumerate(fontsub.charset) if g in glyphs]
			csi=cs.charStringsIndex
			csi.items=[csi.items[i] for i in indices]
			del csi.file, csi.offsets
			if hasattr(fontsub, "FDSelect"):
				sel=fontsub.FDSelect
				sel.format=None
				sel.gidArray=[sel.gidArray[i] for i in indices]
			newCharStrings={}
			for indicesIdx, charsetIdx in enumerate(indices):
				g=fontsub.charset[charsetIdx]
				if g in cs.charStrings:
					newCharStrings[g]=indicesIdx
			cs.charStrings=newCharStrings
		else:
			cs.charStrings={g:v
					  for g,v in cs.charStrings.items()
					  if g in glyphs}
		fontsub.charset=[g for g in fontsub.charset if g in glyphs]
		fontsub.numGlyphs=len(fontsub.charset)
def cffinf():
	if 'CFF ' in font:
		cff=font["CFF "]
		cff.cff.fontNames[0]=cff.cff.fontNames[0].replace('SourceHan', cfg['fontName'].replace(' ', ''))
		cff.cff[0].FamilyName=cff.cff[0].FamilyName.replace('Source Han', cfg['fontName'])
		cff.cff[0].FullName=cff.cff[0].FullName.replace('Source Han', cfg['fontName'])
		cff.cff[0].Notice=cfg['fontCopyright']
		cff.cff[0].CIDFontVersion=float(cfg['fontVersion'])
		for dic in cff.cff[0].FDArray:
			dic.FontName=dic.FontName.replace('SourceHan', cfg['fontName'].replace(' ', ''))
def chguvs(newu):
	for table in font["cmap"].tables:
		if table.format==14:
			for un1 in newu.keys():
				for uv in set(table.uvsDict.keys()):
					if (un1, None) in table.uvsDict[uv]:
						print('remove old uvs', chr(un1))
						table.uvsDict[uv].remove((un1, None))
			for un1 in newu.keys():
				if newu[un1] not in table.uvsDict:
					table.uvsDict[newu[un1]]=list()
				print('use new uvs', chr(un1))
				table.uvsDict[newu[un1]].append((un1, None))
def getjpv():
	cmap=font.getBestCmap()
	jpvar=dict()
	jpvch=[('𰰨', '芲'), ('𩑠', '頙'), ('𥄳', '眔')]
	for chs in jpvch:
		if ord(chs[1]) in cmap:
			jpvar[ord(chs[0])]=cmap[ord(chs[1])]
	return jpvar
def locvar():
	cmap=font.getBestCmap()
	locscv=[('𫜹', '彐'), ('𣽽', '潸')]
	for lv1 in locscv:
		if ord(lv1[1]) in cmap:
			gv2=glfrloc(cmap[ord(lv1[1])], loczhs)
			if gv2:
				print('Processing', lv1[0])
				setcg(ord(lv1[0]), gv2)
def uvsvar():
	uvsmul=[('⺼', '月', 'E0100'), ('𱍐', '示', 'E0100'), ('䶹', '屮', 'E0101'), ('𠾖', '器', 'E0100'), ('𡐨', '壄', 'E0100'), ('𤥨', '琢', 'E0101'), ('𦤀', '臭', 'E0100'), ('𨺓', '隆', 'E0100'), ('𫜸', '叱', 'E0101')]
	for uvm in uvsmul:
		u1, u2, usel=ord(uvm[0]), ord(uvm[1]), int(uvm[2], 16)
		if u2 in uvdic and usel in uvdic[u2]:
			print('Processing', uvm[0])
			setcg(u1, uvdic[u2][usel])
def radicv():
	radic=[('⽉', '月'), ('⻁', '虎'), ('⾳', '音'), ('⿓', '龍'), ('⼾', '戶')]
	cmap=font.getBestCmap()
	for chs in radic:
		if ord(chs[1]) in cmap:
			print('Processing', chs[0])
			setcg(ord(chs[0]), cmap[ord(chs[1])])
def cksh10():
	print('Getting glyphs from SourceHan 1.0x...')
	cmap=font.getBestCmap()
	file10=os.path.join(pydir, f'sourcehan10/SourceHan{ssty}-{wt}{exn}')
	if os.path.isfile(file10):
		get10=dict()
		sh10set=json.load(open(os.path.join(pydir, 'configs/sourcehan10.json'), 'r', encoding='utf-8'))
		font10=TTFont(file10)
		cmap10=font10.getBestCmap()
		for ch10 in sh10set[ssty]:
			if ord(ch10) in cmap and ord(ch10) in cmap10:
				print('Find', ch10)
				get10[cmap[ord(ch10)]]=cmap10[ord(ch10)]
		lockor10, loczht10=getloclk(font10, 'KOR'), getloclk(font10, 'ZHT')
		if ssty!='Serif':
			for ch10 in sh10set['SansTC']:
				gll=glfrloc(cmap10[ord(ch10)], loczht10)
				if ord(ch10) in cmap and gll:
					print('Find', ch10)
					get10[cmap[ord(ch10)]]=gll
		getother(font10, get10)
		font10.close()
	else: print('SourceHan 1.0x Failed!')
def ckckg():
	print('Getting glyphs from ChiuKongGothic...')
	cmap=font.getBestCmap()
	filec=os.path.join(pydir, f'ChiuKongGothic-CL/ChiuKongGothic-CL-{wt}{exn}')
	ckgcf=os.path.join(pydir, 'configs/ChiuKongGothic-CL.json')
	if os.path.isfile(filec) and os.path.isfile(ckgcf):
		getckg=dict()
		fontck=TTFont(filec)
		cmapck=fontck.getBestCmap()
		ofcfg=json.load(open(ckgcf, 'r', encoding='utf-8'))
		if 'chars' in ofcfg:
			for ckch in ofcfg['chars']:
				if ord(ckch) in cmap and ord(ckch) in cmapck:
					print('Find', ckch)
					getckg[cmap[ord(ckch)]]=cmapck[ord(ckch)]
		if 'uvs' in ofcfg:
			newu=dict()
			ckuvs=getuvs(fontck, cmapck)
			for ckch in ofcfg['uvs'].keys():
				if ord(ckch) in cmap and ord(ckch) in ckuvs:
					print('Find', ckch)
					getckg[cmap[ord(ckch)]]=ckuvs[ord(ckch)][int(ofcfg['uvs'][ckch], 16)]
					if ord(ckch) in uvdic:
						newu[ord(ckch)]=int(ofcfg['uvs'][ckch], 16)
			chguvs(newu)
		getother(fontck, getckg)
		fontck.close()
	else: print('ChiuKongGothic Failed!')
def getnewg():
	print('Getting new glyphs...')
	cmap=font.getBestCmap()
	filenew=os.path.join(pydir, f'New/New{ssty}-{wt}{exn}')
	if os.path.isfile(filenew):
		getnew=dict()
		fontnew=TTFont(filenew)
		cmapnew=fontnew.getBestCmap()
		cnsp='写泻画瑶恋峦蛮挛栾滦弯湾'
		for ncd in cmapnew.keys():
			if ncd==0x20 or ncd not in cmap:continue
			chn=chr(ncd)
			print('Find', chn)
			if chn in cnsp:
				g1=glfrloc(cmap[ncd], loczhs)
			else:
				g1=cmap[ncd]
			g2=cmapnew[ncd]
			getnew[g1]=g2
		loczhsnew=getloclk(fontnew, 'ZHS')
		for chn in '禅遥':
			print('Find', chn)
			g1=glfrloc(cmap[ord(chn)], loczhs)
			g2=glfrloc(cmapnew[ord(chn)], loczhsnew)
			getnew[g1]=g2
		getother(fontnew, getnew)
		fontnew.close()
	else: print('Getting new glyphs Failed!')

def subgl():
	cmap=font.getBestCmap()
	pen='"\'—‘’‚“”„‼⁇⁈⁉⸺⸻'
	pzhs='·’‘”“•≤≥≮≯！：；？'+pen
	pzht='·’‘”“•、。，．'+pen
	simpcn='蒋残浅践写泻惮禅箪蝉恋峦蛮挛栾滦弯湾径茎滞画遥瑶'#変将与弥称
	usedg=set()
	usedg.add('.notdef')
	usedg.update(cmap.values())
	usedg.update(uvgls)
	pungl=glfrtxt(pzhs+pzht+simpcn)
	print('Checking Lookup table...')
	loclks=list()
	for i in range(len(font["GSUB"].table.FeatureList.FeatureRecord)):
		if font["GSUB"].table.FeatureList.FeatureRecord[i].FeatureTag=='locl':
			loclks+=font["GSUB"].table.FeatureList.FeatureRecord[i].Feature.LookupListIndex
	for lki in set(loclks):
		for st in font["GSUB"].table.LookupList.Lookup[lki].SubTable:
			if st.LookupType==7:
				stbl=st.ExtSubTable
			else:
				stbl=st
			assert stbl.LookupType==1
			tabl=stbl.mapping
			for k1 in list(tabl.keys()):
				if k1 in pungl or tabl[k1] in pungl:
					usedg.add(k1)
					usedg.add(tabl[k1])
				else:
					del tabl[k1]
	for ki in font["GSUB"].table.LookupList.Lookup:
		for st in ki.SubTable:
			if st.LookupType==7:
				stbl=st.ExtSubTable
			else:
				stbl=st
			lktp=stbl.LookupType
			if lktp==1:
				tabl=stbl.mapping
				for g1, g2 in list(tabl.items()):
					if g1 in usedg:
						usedg.add(g2)
					else:
						del tabl[g1]
			elif lktp==3:
				for item in list(stbl.alternates.keys()):
					if item in usedg:
						usedg.update(set(stbl.alternates[item]))
					else:
						del stbl.alternates[item]
			elif lktp==4:
				for li in list(stbl.ligatures):
					for lg in list(stbl.ligatures[li]):
						a=list(lg.Component)
						a.append(li)
						if set(a).issubset(usedg):
							usedg.add(lg.LigGlyph)
						else:
							stbl.ligatures[li].remove(lg)
					if len(stbl.ligatures[li])<1:
						del stbl.ligatures[li]
			elif lktp==5:
				if hasattr(stbl, 'Coverage'):
					for tb in stbl.Coverage:
						usedg.update(tb.glyphs)
			elif lktp==6:
				for tb in stbl.BacktrackCoverage:
					usedg.update(tb.glyphs)
				for tb in stbl.InputCoverage:
					usedg.update(tb.glyphs)
				for tb in stbl.LookAheadCoverage:
					usedg.update(tb.glyphs)
			else: raise
	for ki in font["GPOS"].table.LookupList.Lookup:
		for st in ki.SubTable:
			if st.LookupType==9:
				stbl=st.ExtSubTable
			else:
				stbl=st
			lktp=stbl.LookupType
			if lktp==1:
				coverage=stbl.Coverage
				coverage.glyphs=[g for g in coverage.glyphs if g in usedg]
			elif lktp==2:
				coverage=stbl.Coverage
				coverage.glyphs=[g for g in coverage.glyphs if g in usedg]
				if stbl.Format==1:
					for pair in stbl.PairSet:
						pair.PairValueRecord=[vr for vr in pair.PairValueRecord if vr.SecondGlyph in usedg]
				elif stbl.Format==2:
					stbl.ClassDef1.classDefs={cld:stbl.ClassDef1.classDefs[cld] for cld in stbl.ClassDef1.classDefs.keys() if cld in usedg}
					stbl.ClassDef2.classDefs={cld:stbl.ClassDef2.classDefs[cld] for cld in stbl.ClassDef2.classDefs.keys() if cld in usedg}
			elif lktp==4:
				markcoverage=stbl.MarkCoverage
				markcoverage.glyphs=[g for g in markcoverage.glyphs if g in usedg]
				basecoverage=stbl.BaseCoverage
				basecoverage.glyphs=[g for g in basecoverage.glyphs if g in usedg]
			else:
				raise
	nnnd=list()
	for fl in font.getGlyphOrder():
		if fl in usedg or fl in ('.notdef', '.null', 'nonmarkingreturn', 'NULL', 'NUL'):
			nnnd.append(fl)
		else:
			if 'VORG' in font and fl in font['VORG'].VOriginRecords:
				del font['VORG'].VOriginRecords[fl]
			if 'gvar' in font and fl in font['gvar'].variations:
				del font['gvar'].variations[fl]
			del font['hmtx'][fl]
			del font['vmtx'][fl]
	if 'CFF ' in font:
		subcff(font['CFF '], set(nnnd))
	elif 'CFF2' in font:
		subcff(font['CFF2'], set(nnnd))
	elif 'glyf' in font:
		font['glyf'].glyphs={g:font['glyf'].glyphs[g] for g in set(nnnd)}
	font.setGlyphOrder(nnnd)
def ckcngg():
	cmap=font.getBestCmap()
	for table in font["cmap"].tables:
		if table.format==14:
			cdg=ord('关')
			if 0xE0102 in table.uvsDict and (cdg, None) in table.uvsDict[0xE0102]: return
			for uv in table.uvsDict[0xE0101]:
				if uv[0]==cdg:
					cngg=uv[1]
					break
			if not cngg: return
			table.uvsDict[0xE0100]=[uv for uv in table.uvsDict[0xE0100] if uv[0]!=cdg]
			table.uvsDict[0xE0101]=[uv for uv in table.uvsDict[0xE0101] if uv[0]!=cdg]
			table.uvsDict[0xE0100].append((cdg, cmap[cdg]))
			table.uvsDict[0xE0101].append((cdg, None))
			print('Remapping', '关')
			setcg(cdg, cngg)
def glfruv(ch, uv):
	cmap=font.getBestCmap()
	for table in font["cmap"].tables:
		if table.format==14 and uv in table.uvsDict:
			for cg in table.uvsDict[uv]:
				if cg[0]==ord(ch):
					if cg[1]==None: return cmap[cg[0]]
					else: return cg[1]
	raise RuntimeError(ch)
def ckdlg():
	rplg=dict()
	for ch in '月成':
		rplg[glfruv(ch, 0xE0100)]=glfruv(ch, 0xE0101)
	dllk=set()
	for ki in font["GSUB"].table.FeatureList.FeatureRecord:
		if ki.FeatureTag=='dlig': dllk.update(ki.Feature.LookupListIndex)
	for i in dllk:
		for st in font["GSUB"].table.LookupList.Lookup[i].SubTable:
			if st.LookupType==7: stbl=st.ExtSubTable
			else: stbl=st
			if stbl.LookupType!=4: continue
			for lgg in list(stbl.ligatures):
				for lg in list(stbl.ligatures[lgg]):
					for ilin in range(len(lg.Component)):
						if lg.Component[ilin] in rplg:
							lg.Component[ilin]=rplg[lg.Component[ilin]]

print('*'*50)
print('====Build Advocate Ancient Fonts====\n')
infile=sys.argv[1]
outfile=sys.argv[2]

font=TTFont(infile)
fpsn=font["name"].getDebugName(6)
ssty=str()
if 'Sans' in fpsn or 'Mono' in fpsn: ssty='Sans'
elif 'Serif' in fpsn: ssty='Serif'
if 'CFF ' in font or 'CFF2' in font: exn='.otf'
elif 'glyf' in font: exn='.ttf'
else: raise
wtn={250:'ExtraLight', 300:'Light', 350:'Normal', 400:'Regular', 500:'Medium', 600:'SemiBold', 700:'Bold', 900:'Heavy'}
wt=wtn[font['OS/2'].usWeightClass]
if 'VF' in fpsn: wt='VF'
cffinf()

jpvar=getjpv()
print('Getting the localized lookups table...')
lockor, loczhs, loczht, loczhh=getloclk(font, 'KOR'), getloclk(font, 'ZHS'), getloclk(font, 'ZHT'), getloclk(font, 'ZHH')
locgls=locglrpl()
print('Getting uvs...')
uvdic, uvgls=uvstab()
print('Processing localized glyphs...')
glyrepl(locgls)
print('Processing locl Variant ...')
locvar()
for jco in jpvar.keys():
	setcg(jco, jpvar[jco])
print('Processing uvs glyphs...')
setuvs()
print('Processing uvs Variant...')
uvsvar()
ftuvstab()
print('Processing radicals...')
radicv()
ckdlg()
print('Getting glyphs from other fonts...')
if ssty=='Sans': ckckg()
getnewg()
cksh10()
ckcngg()
print('Checking for unused glyphs...')
subgl()
print('Saving font...')
font.save(outfile)
print('Finished!')
print('*'*50)
