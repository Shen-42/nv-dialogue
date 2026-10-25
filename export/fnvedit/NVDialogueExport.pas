{
  NVDialogueExport.pas - FNVEdit (xEdit) script for card 2.

  Exports dialogue, actors, factions and quests from one plugin to CSV:
    lines.csv     one row per response (an INFO can hold several)
    npcs.csv      NPC_ and CREA records with their factions
    factions.csv  FACT records
    quests.csv    QUST records
    export_report.txt  line counts per quest

  How to run:
    1. Copy this file into FNVEdit's "Edit Scripts" folder.
    2. Start FNVEdit and load FalloutNV.esm only.
    3. Right-click FalloutNV.esm in the left pane > Apply Script >
       NVDialogueExport.
    4. Files land in <FNVEdit folder>\NVDialogueExport\FalloutNV.esm\.
       Copy them to data/export/ in the repo, then run
       python ingest/check_export.py data/export

  Only records that originate in the selected plugin are exported, so
  running it on a DLC plugin later (card 12) skips base-game overrides.

  Field paths follow FNVEdit's record definitions. If a column comes out
  blank for every row, open one INFO record in FNVEdit and compare its
  field names with the paths in ReadSpeaker and ExportInfo below.
}
unit NVDialogueExport;

var
  slLines, slActors, slFactions, slQuests, slQuestCounts: TStringList;
  gSpeaker: IInterface;
  gConds: string;
  gPlugin: string;
  nLines, nNoSpeaker, nNoQuest: integer;

function Csv(s: string): string;
begin
  s := StringReplace(s, #13#10, ' ', [rfReplaceAll]);
  s := StringReplace(s, #13, ' ', [rfReplaceAll]);
  s := StringReplace(s, #10, ' ', [rfReplaceAll]);
  s := StringReplace(s, '"', '""', [rfReplaceAll]);
  Result := '"' + s + '"';
end;

function Fid(e: IInterface): string;
begin
  if Assigned(e) then
    Result := IntToHex(GetLoadOrderFormID(e), 8)
  else
    Result := '';
end;

function Edid(e: IInterface): string;
begin
  if Assigned(e) then
    Result := EditorID(e)
  else
    Result := '';
end;

function FullName(e: IInterface): string;
begin
  if Assigned(e) then
    Result := GetElementEditValues(e, 'FULL')
  else
    Result := '';
end;

function IsActor(e: IInterface): boolean;
begin
  Result := False;
  if Assigned(e) then
    Result := (Signature(e) = 'NPC_') or (Signature(e) = 'CREA');
end;

procedure AddCond(s: string);
begin
  if gConds = '' then
    gConds := s
  else
    gConds := gConds + '; ' + s;
end;

{ Sets gSpeaker to the actor who says the line, if one is named, and
  gConds to the other conditions that narrow who can say it. }
procedure ReadSpeaker(info: IInterface);
var
  conds, c, param: IInterface;
  i: integer;
  func, runOn: string;
begin
  gSpeaker := nil;
  gConds := '';

  { Some INFO records name the speaker directly. }
  param := LinksTo(ElementBySignature(info, 'ANAM'));
  if IsActor(param) then
    gSpeaker := param;

  conds := ElementByName(info, 'Conditions');
  for i := 0 to ElementCount(conds) - 1 do begin
    c := ElementByIndex(conds, i);
    func := GetElementEditValues(c, 'CTDA\Function');
    runOn := GetElementEditValues(c, 'CTDA\Run On');
    param := LinksTo(ElementByPath(c, 'CTDA\Parameter #1'));

    { Conditions run on the Target describe the listener, not the speaker. }
    if (runOn <> '') and (runOn <> 'Subject') then
      Continue;

    if (func = 'GetIsID') and IsActor(param) and (not Assigned(gSpeaker)) then
      gSpeaker := param
    else if (func = 'GetIsID') or (func = 'GetInFaction') or
            (func = 'GetIsVoiceType') or (func = 'GetIsClass') or
            (func = 'GetIsRace') then
      AddCond(func + ' ' + Edid(param));
  end;
end;

procedure CountQuest(key: string);
begin
  if key = '' then
    key := '(no quest)';
  slQuestCounts.Values[key] :=
    IntToStr(StrToIntDef(slQuestCounts.Values[key], 0) + 1);
end;

procedure ExportInfo(info: IInterface);
var
  dial, quest, resps, resp: IInterface;
  i: integer;
  text: string;
begin
  { An INFO sits in its topic's child group; ChildrenOf gives the DIAL. }
  dial := ChildrenOf(GetContainer(info));

  quest := LinksTo(ElementBySignature(info, 'QSTI'));
  if (not Assigned(quest)) and Assigned(dial) then
    quest := LinksTo(ElementBySignature(dial, 'QSTI'));

  ReadSpeaker(info);

  resps := ElementByName(info, 'Responses');
  for i := 0 to ElementCount(resps) - 1 do begin
    resp := ElementByIndex(resps, i);
    text := GetElementEditValues(resp, 'NAM1');
    if Trim(text) = '' then
      Continue;

    slLines.Add(
      Csv(Fid(info)) + ',' +
      IntToStr(i + 1) + ',' +
      Csv(Fid(dial)) + ',' +
      Csv(Edid(dial)) + ',' +
      Csv(FullName(dial)) + ',' +
      Csv(Fid(quest)) + ',' +
      Csv(Edid(quest)) + ',' +
      Csv(Fid(gSpeaker)) + ',' +
      Csv(Edid(gSpeaker)) + ',' +
      Csv(FullName(gSpeaker)) + ',' +
      Csv(gConds) + ',' +
      Csv(text) + ',' +
      Csv(gPlugin));

    Inc(nLines);
    if not Assigned(gSpeaker) then
      Inc(nNoSpeaker);
    if not Assigned(quest) then
      Inc(nNoQuest);
    CountQuest(Edid(quest));
  end;
end;

procedure ExportActor(e: IInterface);
var
  facs, f: IInterface;
  i: integer;
  list: string;
begin
  list := '';
  facs := ElementByName(e, 'Factions');
  for i := 0 to ElementCount(facs) - 1 do begin
    f := ElementByIndex(facs, i);
    if list <> '' then
      list := list + ';';
    list := list + Fid(LinksTo(ElementByPath(f, 'Faction'))) + ':' +
            GetElementEditValues(f, 'Rank');
  end;

  slActors.Add(
    Csv(Fid(e)) + ',' +
    Csv(Edid(e)) + ',' +
    Csv(FullName(e)) + ',' +
    Csv(Signature(e)) + ',' +
    Csv(list) + ',' +
    Csv(gPlugin));
end;

procedure ExportNamed(sl: TStringList; e: IInterface);
begin
  sl.Add(Csv(Fid(e)) + ',' + Csv(Edid(e)) + ',' + Csv(FullName(e)) + ',' +
         Csv(gPlugin));
end;

function Initialize: integer;
begin
  slLines := TStringList.Create;
  slActors := TStringList.Create;
  slFactions := TStringList.Create;
  slQuests := TStringList.Create;
  slQuestCounts := TStringList.Create;

  slLines.Add('info_form_id,response_index,topic_form_id,topic_editor_id,' +
              'topic_text,quest_form_id,quest_editor_id,speaker_form_id,' +
              'speaker_editor_id,speaker_name,speaker_conditions,text,source_file');
  slActors.Add('form_id,editor_id,name,record_type,factions,source_file');
  slFactions.Add('form_id,editor_id,name,source_file');
  slQuests.Add('form_id,editor_id,name,source_file');

  gPlugin := '';
  nLines := 0;
  nNoSpeaker := 0;
  nNoQuest := 0;
  Result := 0;
end;

function Process(e: IInterface): integer;
var
  sig: string;
begin
  Result := 0;

  { Skip records that override another plugin's record. }
  if not Equals(MasterOrSelf(e), e) then
    Exit;

  if gPlugin = '' then
    gPlugin := GetFileName(GetFile(e));

  sig := Signature(e);
  if sig = 'INFO' then
    ExportInfo(e)
  else if (sig = 'NPC_') or (sig = 'CREA') then
    ExportActor(e)
  else if sig = 'FACT' then
    ExportNamed(slFactions, e)
  else if sig = 'QUST' then
    ExportNamed(slQuests, e);
end;

function Finalize: integer;
var
  outDir: string;
  report: TStringList;
  i: integer;
begin
  outDir := ProgramPath + 'NVDialogueExport\' + gPlugin + '\';
  ForceDirectories(outDir);

  slLines.SaveToFile(outDir + 'lines.csv');
  slActors.SaveToFile(outDir + 'npcs.csv');
  slFactions.SaveToFile(outDir + 'factions.csv');
  slQuests.SaveToFile(outDir + 'quests.csv');

  report := TStringList.Create;
  report.Add('Plugin: ' + gPlugin);
  report.Add('Lines: ' + IntToStr(nLines));
  report.Add('Lines with no named speaker: ' + IntToStr(nNoSpeaker));
  report.Add('Lines with no quest: ' + IntToStr(nNoQuest));
  report.Add('Actors: ' + IntToStr(slActors.Count - 1));
  report.Add('Factions: ' + IntToStr(slFactions.Count - 1));
  report.Add('Quests: ' + IntToStr(slQuests.Count - 1));
  report.Add('');
  report.Add('Lines per quest:');
  slQuestCounts.Sort;
  for i := 0 to slQuestCounts.Count - 1 do
    report.Add('  ' + slQuestCounts.Names[i] + ' ' +
               slQuestCounts.Values[slQuestCounts.Names[i]]);
  report.SaveToFile(outDir + 'export_report.txt');

  AddMessage('NVDialogueExport: ' + IntToStr(nLines) + ' lines written to ' + outDir);

  report.Free;
  slLines.Free;
  slActors.Free;
  slFactions.Free;
  slQuests.Free;
  slQuestCounts.Free;
  Result := 0;
end;

end.
