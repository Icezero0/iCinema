param(
  [Parameter(Mandatory = $true)][string]$ExePath,
  [Parameter(Mandatory = $true)][string]$IconPath
)

$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;

public static class IcinemaExeIcon
{
    private const int RtIcon = 3;
    private const int RtGroupIcon = 14;
    private const int LoadLibraryAsDataFile = 2;
    private const int ResourceTypeNotFound = 1813;
    private const int FirstIconId = 40000;

    private sealed class ResourceName
    {
        public int Id;
        public string Text;

        public static ResourceName FromPointer(IntPtr pointer)
        {
            long value = pointer.ToInt64();
            if (value >= 0 && value <= ushort.MaxValue)
                return new ResourceName { Id = (int)value };
            return new ResourceName { Text = Marshal.PtrToStringUni(pointer) };
        }
    }

    private sealed class GroupTarget
    {
        public ResourceName Name;
        public ushort Language;
    }

    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    private delegate bool ResourceNameCallback(IntPtr module, IntPtr type, IntPtr name, IntPtr parameter);

    [UnmanagedFunctionPointer(CallingConvention.Winapi)]
    private delegate bool ResourceLanguageCallback(IntPtr module, IntPtr type, IntPtr name, ushort language, IntPtr parameter);

    [DllImport("kernel32.dll", EntryPoint = "LoadLibraryExW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr LoadLibraryEx(string fileName, IntPtr file, int flags);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool FreeLibrary(IntPtr module);

    [DllImport("kernel32.dll", EntryPoint = "EnumResourceNamesW", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumResourceNames(IntPtr module, IntPtr type, ResourceNameCallback callback, IntPtr parameter);

    [DllImport("kernel32.dll", EntryPoint = "EnumResourceLanguagesW", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumResourceLanguages(IntPtr module, IntPtr type, IntPtr name, ResourceLanguageCallback callback, IntPtr parameter);

    [DllImport("kernel32.dll", EntryPoint = "BeginUpdateResourceW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr BeginUpdateResource(string fileName, [MarshalAs(UnmanagedType.Bool)] bool deleteExisting);

    [DllImport("kernel32.dll", EntryPoint = "UpdateResourceW", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool UpdateResource(IntPtr update, IntPtr type, IntPtr name, ushort language, byte[] data, uint size);

    [DllImport("kernel32.dll", EntryPoint = "EndUpdateResourceW", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EndUpdateResource(IntPtr update, [MarshalAs(UnmanagedType.Bool)] bool discard);

    private static List<GroupTarget> ExistingGroups(string executable)
    {
        var groups = new List<GroupTarget>();
        IntPtr module = LoadLibraryEx(executable, IntPtr.Zero, LoadLibraryAsDataFile);
        if (module == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        try
        {
            int enumerationError = 0;
            ResourceNameCallback names = delegate(IntPtr loaded, IntPtr type, IntPtr name, IntPtr parameter)
            {
                ResourceName captured = ResourceName.FromPointer(name);
                ResourceLanguageCallback languages = delegate(IntPtr unusedModule, IntPtr unusedType, IntPtr unusedName, ushort language, IntPtr unusedParameter)
                {
                    groups.Add(new GroupTarget { Name = captured, Language = language });
                    return true;
                };
                if (!EnumResourceLanguages(loaded, type, name, languages, IntPtr.Zero))
                    enumerationError = Marshal.GetLastWin32Error();
                GC.KeepAlive(languages);
                return enumerationError == 0;
            };
            bool found = EnumResourceNames(module, new IntPtr(RtGroupIcon), names, IntPtr.Zero);
            int nameError = found ? 0 : Marshal.GetLastWin32Error();
            GC.KeepAlive(names);
            if (enumerationError != 0) throw new Win32Exception(enumerationError);
            if (!found && nameError != ResourceTypeNotFound) throw new Win32Exception(nameError);
        }
        finally
        {
            FreeLibrary(module);
        }
        if (groups.Count == 0)
            groups.Add(new GroupTarget { Name = new ResourceName { Id = 1 }, Language = 1033 });
        return groups;
    }

    private static void PutResource(IntPtr update, int type, ResourceName name, ushort language, byte[] data)
    {
        IntPtr identifier = name.Text == null ? new IntPtr(name.Id) : Marshal.StringToHGlobalUni(name.Text);
        try
        {
            if (!UpdateResource(update, new IntPtr(type), identifier, language, data, (uint)data.Length))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        finally
        {
            if (name.Text != null) Marshal.FreeHGlobal(identifier);
        }
    }

    public static void Apply(string executable, string iconFile)
    {
        byte[] icon = File.ReadAllBytes(iconFile);
        var images = new List<byte[]>();
        byte[] group;
        using (var input = new BinaryReader(new MemoryStream(icon)))
        {
            if (icon.Length < 6 || input.ReadUInt16() != 0 || input.ReadUInt16() != 1)
                throw new InvalidDataException("Expected a Windows .ico file");
            int count = input.ReadUInt16();
            if (count < 1 || count > 100 || icon.Length < 6 + count * 16)
                throw new InvalidDataException("Invalid .ico image count");

            using (var output = new MemoryStream())
            using (var writer = new BinaryWriter(output))
            {
                writer.Write((ushort)0);
                writer.Write((ushort)1);
                writer.Write((ushort)count);
                for (int i = 0; i < count; i++)
                {
                    int entry = 6 + i * 16;
                    uint size = BitConverter.ToUInt32(icon, entry + 8);
                    uint offset = BitConverter.ToUInt32(icon, entry + 12);
                    if (size == 0 || (ulong)offset + size > (ulong)icon.Length)
                        throw new InvalidDataException("Invalid .ico image offset or size");
                    var image = new byte[size];
                    Buffer.BlockCopy(icon, (int)offset, image, 0, (int)size);
                    images.Add(image);
                    writer.Write(icon, entry, 12);
                    writer.Write((ushort)(FirstIconId + i));
                }
                group = output.ToArray();
            }
        }

        List<GroupTarget> targets = ExistingGroups(executable);
        IntPtr update = BeginUpdateResource(executable, false);
        if (update == IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error());
        bool committed = false;
        try
        {
            var languages = new HashSet<ushort>();
            foreach (GroupTarget target in targets) languages.Add(target.Language);
            foreach (ushort language in languages)
                for (int i = 0; i < images.Count; i++)
                    PutResource(update, RtIcon, new ResourceName { Id = FirstIconId + i }, language, images[i]);
            foreach (GroupTarget target in targets)
                PutResource(update, RtGroupIcon, target.Name, target.Language, group);
            if (!EndUpdateResource(update, false)) throw new Win32Exception(Marshal.GetLastWin32Error());
            committed = true;
        }
        finally
        {
            if (!committed) EndUpdateResource(update, true);
        }
    }
}
'@ -ErrorAction Stop

[IcinemaExeIcon]::Apply((Resolve-Path -LiteralPath $ExePath).Path, (Resolve-Path -LiteralPath $IconPath).Path)
