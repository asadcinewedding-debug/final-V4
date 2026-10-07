using System.Reflection;
using System.Text;
using System.Windows.Forms;

namespace ANAIRelightV4Setup;

internal static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new InstallerForm());
    }
}

public sealed class InstallerForm : Form
{
    readonly Color Bg = Color.FromArgb(12, 18, 32);
    readonly Color Card = Color.FromArgb(24, 34, 54);
    readonly Color Card2 = Color.FromArgb(31, 44, 70);
    readonly Color Cyan = Color.FromArgb(0, 188, 212);
    readonly Color Purple = Color.FromArgb(126, 87, 194);
    readonly Color Green = Color.FromArgb(76, 175, 80);
    readonly Color Amber = Color.FromArgb(255, 193, 7);
    readonly Color TextMain = Color.FromArgb(245, 248, 255);
    readonly Color TextMuted = Color.FromArgb(174, 188, 212);

    readonly TextBox modulesBox = new();
    readonly TextBox logBox = new();
    readonly Button browseButton = new();
    readonly Button installButton = new();
    readonly Label status = new();

    public InstallerForm()
    {
        Text = "AN AI Relight V4 — Creative Relight Installer";
        Width = 790;
        Height = 620;
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        BackColor = Bg;
        ForeColor = TextMain;
        Font = new Font("Segoe UI", 10f);

        BuildUi();

        modulesBox.Text = DefaultModules();
        browseButton.Click += (_,__) => Browse();
        installButton.Click += (_,__) => Install();
    }

    Label L(string text,float size=10f,FontStyle style=FontStyle.Regular,Color? color=null)
        => new() {
            Text=text, AutoSize=true, ForeColor=color ?? TextMain, BackColor=Color.Transparent,
            Font=new Font("Segoe UI",size,style)
        };

    Panel CardPanel(int height)
        => new() { Width=720, Height=height, BackColor=Card, Margin=new Padding(0,8,0,8), Padding=new Padding(18) };

    void BuildUi()
    {
        var root=new FlowLayoutPanel {
            Dock=DockStyle.Fill, FlowDirection=FlowDirection.TopDown, WrapContents=false,
            AutoScroll=true, Padding=new Padding(24), BackColor=Bg
        };

        var hero=new Panel { Width=720, Height=122, BackColor=Color.FromArgb(18,31,55), Margin=new Padding(0,0,0,10) };
        var bar1=new Panel { Dock=DockStyle.Left, Width=7, BackColor=Cyan };
        var bar2=new Panel { Dock=DockStyle.Right, Width=7, BackColor=Purple };
        hero.Controls.Add(bar1); hero.Controls.Add(bar2);
        var title=L("AN AI RELIGHT V4",23f,FontStyle.Bold);
        title.Location=new Point(28,18);
        var sub=L("Creative Subject + Scene Relighting for Lightroom Classic",10.5f,FontStyle.Regular,TextMuted);
        sub.Location=new Point(30,60);
        var badge=L("DEPTH  •  MATTING  •  SCENE MOOD  •  CREATIVE FINISH  •  BATCH",9f,FontStyle.Bold,Cyan);
        badge.Location=new Point(30,87);
        hero.Controls.Add(title); hero.Controls.Add(sub); hero.Controls.Add(badge);
        root.Controls.Add(hero);

        var location=CardPanel(142);
        var lt=L("INSTALL LOCATION",11f,FontStyle.Bold,Cyan); lt.Location=new Point(18,14);
        var hint=L("Lightroom Modules folder",9.5f,FontStyle.Regular,TextMuted); hint.Location=new Point(18,42);
        modulesBox.SetBounds(18,68,555,32);
        modulesBox.BackColor=Card2; modulesBox.ForeColor=TextMain; modulesBox.BorderStyle=BorderStyle.FixedSingle;
        browseButton.Text="Browse"; browseButton.SetBounds(585,67,105,34);
        browseButton.FlatStyle=FlatStyle.Flat; browseButton.FlatAppearance.BorderColor=Cyan;
        browseButton.BackColor=Color.FromArgb(22,70,90); browseButton.ForeColor=TextMain; browseButton.Cursor=Cursors.Hand;
        var pi=L(@"Installs to  AN AI Relight.lrplugin  •  existing version is backed up first",9f,FontStyle.Bold,Amber);
        pi.Location=new Point(18,110);
        location.Controls.Add(lt);location.Controls.Add(hint);location.Controls.Add(modulesBox);location.Controls.Add(browseButton);location.Controls.Add(pi);
        root.Controls.Add(location);

        var features=CardPanel(132);
        var ft=L("V4 ENGINE",11f,FontStyle.Bold,Purple); ft.Location=new Point(18,12);
        var f1=L("●  MODNet Photographic human matting",9.5f); f1.Location=new Point(18,42);
        var f2=L("●  Depth Anything V2 scene depth",9.5f); f2.Location=new Point(350,42);
        var f3=L("●  Face-aware subject light + rim light",9.5f); f3.Location=new Point(18,70);
        var f4=L("●  Background mood + light spill + separation",9.5f); f4.Location=new Point(350,70);
        var f5=L("●  Contrast + bloom + vignette + color finish",9.5f); f5.Location=new Point(18,98);
        features.Controls.Add(ft);features.Controls.Add(f1);features.Controls.Add(f2);features.Controls.Add(f3);features.Controls.Add(f4);features.Controls.Add(f5);
        root.Controls.Add(features);

        installButton.Text="INSTALL AN AI RELIGHT V4";
        installButton.Width=720; installButton.Height=50;
        installButton.FlatStyle=FlatStyle.Flat; installButton.FlatAppearance.BorderSize=0;
        installButton.BackColor=Green; installButton.ForeColor=Color.White;
        installButton.Font=new Font("Segoe UI",11.5f,FontStyle.Bold); installButton.Cursor=Cursors.Hand;
        installButton.Margin=new Padding(0,6,0,10);
        root.Controls.Add(installButton);

        status.AutoSize=true; status.ForeColor=Cyan; status.Font=new Font("Segoe UI",9.5f,FontStyle.Bold);
        status.Margin=new Padding(2,0,0,8); root.Controls.Add(status);

        logBox.Width=720; logBox.Height=125; logBox.Multiline=true; logBox.ReadOnly=true; logBox.ScrollBars=ScrollBars.Vertical;
        logBox.BackColor=Color.FromArgb(8,13,24); logBox.ForeColor=Color.FromArgb(190,230,242);
        logBox.BorderStyle=BorderStyle.FixedSingle; logBox.Font=new Font("Consolas",9f);
        root.Controls.Add(logBox);

        Controls.Add(root);
    }

    static string DefaultModules()
    {
        var appData=Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        return Path.Combine(appData,"Adobe","Lightroom","Modules");
    }

    void Browse()
    {
        using var d=new FolderBrowserDialog {
            Description="Select Lightroom's Modules folder",
            UseDescriptionForTitle=true,
            SelectedPath=Directory.Exists(modulesBox.Text) ? modulesBox.Text : DefaultModules()
        };
        if(d.ShowDialog(this)==DialogResult.OK) modulesBox.Text=d.SelectedPath;
    }

    void Log(string s)
    {
        logBox.AppendText("> "+s+Environment.NewLine);
        logBox.SelectionStart=logBox.TextLength;
        logBox.ScrollToCaret();
        Application.DoEvents();
    }

    static byte[] ResourceBytes(string name)
    {
        var asm=Assembly.GetExecutingAssembly();
        using var s=asm.GetManifestResourceStream(name) ?? throw new InvalidOperationException("Missing installer resource: "+name);
        using var ms=new MemoryStream();
        s.CopyTo(ms);
        return ms.ToArray();
    }

    static string ResourceText(string name)=>Encoding.UTF8.GetString(ResourceBytes(name));

    static void WriteText(string path,string data)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path,data,new UTF8Encoding(false));
    }

    static void WriteBytes(string path,byte[] data)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path,data);
    }

    void Install()
    {
        installButton.Enabled=false;
        installButton.BackColor=Color.FromArgb(70,100,80);
        status.ForeColor=Cyan;
        status.Text="Installing V4...";
        try
        {
            var modules=modulesBox.Text.Trim().Trim('"');
            if(modules.Length==0) throw new InvalidOperationException("Choose a Lightroom Modules folder.");
            Directory.CreateDirectory(modules);

            var root=Path.Combine(modules,"AN AI Relight.lrplugin");
            if(Directory.Exists(root))
            {
                var backup=Path.Combine(modules,"AN AI Relight Backup-"+DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.Move(root,backup);
                Log("Previous AN AI Relight backed up:");
                Log(backup);
            }

            Directory.CreateDirectory(root);
            Directory.CreateDirectory(Path.Combine(root,"engine"));
            Directory.CreateDirectory(Path.Combine(root,"licenses"));

            Log("Installing V4 Lightroom files...");
            WriteText(Path.Combine(root,"Info.lua"),ResourceText("Info.lua"));
            WriteText(Path.Combine(root,"Core.lua"),ResourceText("Core.lua"));
            WriteText(Path.Combine(root,"Engine.lua"),ResourceText("Engine.lua"));
            WriteText(Path.Combine(root,"Relight.lua"),ResourceText("Relight.lua"));
            WriteText(Path.Combine(root,"Relighting.lua"),ResourceText("Relighting.lua"));

            Log("Installing V4 offline AI engine...");
            WriteBytes(Path.Combine(root,"engine","relight_engine.exe"),ResourceBytes("relight_engine.exe"));
            WriteText(Path.Combine(root,"licenses","MODNET-LICENSE.txt"),ResourceText("MODNET-LICENSE.txt"));
            WriteText(Path.Combine(root,"licenses","DEPTH-ANYTHING-V2-LICENSE.txt"),ResourceText("DEPTH-ANYTHING-V2-LICENSE.txt"));
            WriteText(Path.Combine(root,"licenses","OPENCV-LICENSE.txt"),ResourceText("OPENCV-LICENSE.txt"));

            foreach(var f in new[]{
                Path.Combine(root,"Info.lua"),Path.Combine(root,"Core.lua"),
                Path.Combine(root,"Relighting.lua"),Path.Combine(root,"engine","relight_engine.exe")
            })
                if(!File.Exists(f) || new FileInfo(f).Length==0)
                    throw new IOException("Installation verification failed: "+f);

            Log("V4 installation verified");
            Log("AN AI Edit remains untouched");
            status.ForeColor=Green;
            status.Text="✓ AN AI Relight V4 installed successfully";
            installButton.BackColor=Green;

            MessageBox.Show(this,
                "AN AI Relight V4 was installed successfully.\n\nRestart Lightroom Classic, select photos, then open:\nFile > Plug-in Extras > AN AI Relight V4 — Creative Batch...",
                "AN AI Relight V4",MessageBoxButtons.OK,MessageBoxIcon.Information);
        }
        catch(Exception ex)
        {
            status.ForeColor=Color.FromArgb(244,67,54);
            status.Text="✕ Installation failed";
            Log("ERROR: "+ex.Message);
            MessageBox.Show(this,ex.Message,"AN AI Relight V4 — Installer Error",MessageBoxButtons.OK,MessageBoxIcon.Error);
        }
        finally
        {
            installButton.Enabled=true;
            if(status.ForeColor!=Color.FromArgb(244,67,54)) installButton.BackColor=Green;
        }
    }
}
